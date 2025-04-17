# Backend/services/vector_storage.py
"""
Verbesserte Vektordatenbank-Schnittstelle mit optimiertem Caching, 
Fehlerbehandlung und zentraler Konfiguration.
Diese Datei ersetzt services/vector_db.py und bietet eine sauberere API.
"""
import os
import chromadb
import logging
import json
import uuid
import re
import time
import threading
from typing import List, Dict, Any, Optional, Union, Tuple
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from datetime import datetime

from config import config_manager
from utils.error_handler import APIError

# Logger konfigurieren
logger = logging.getLogger(__name__)

# Thread-Lock für Datenbank-Operationen
_db_lock = threading.RLock()

# Singleton-Instanz
_vector_storage = None

class VectorStorage:
    """
    Verbesserte Vektordatenbank-Schnittstelle mit optimiertem Caching und Fehlerbehandlung.
    Implementiert das Singleton-Pattern.
    """
    
    def __init__(self):
        """Initialisiert die Vektordatenbank-Schnittstelle"""
        self.client = None
        self.embedding_function = None
        self.persist_dir = config_manager.get('CHROMA_PERSIST_DIR', './data/chroma')
        
        # Cache für Suchanfragen
        self._search_cache = {}
        self._cache_ttl = 60 * 60  # 1 Stunde Cache-TTL
        self._max_cache_size = 100
        self._cache_lock = threading.RLock()
        
        # Initialisiere Embedding-Funktion
        self._init_embedding_function()
        
        # Initialisiere ChromaDB-Client
        self._init_client()
    
    def _init_embedding_function(self):
        """Initialisiert die Embedding-Funktion basierend auf der Konfiguration"""
        embedding_function_name = config_manager.get('EMBEDDING_FUNCTION', 'ollama')
        
        try:
            if embedding_function_name == 'ollama':
                # Versuche, OllamaEmbeddingFunction zu importieren
                try:
                    from .ollama_embeddings import OllamaEmbeddingFunction
                    
                    ollama_url = config_manager.get('OLLAMA_API_URL', 'http://localhost:11434')
                    ollama_model = config_manager.get('OLLAMA_MODEL', 'llama3')
                    
                    # Dimension explizit setzen, basierend auf dem Modell
                    fallback_dimension = 384  # Default für die meisten Basis-Modelle
                    
                    # Modellspezifische Dimensionen
                    model_dimensions = {
                        'llama3': 4096,
                        'mistral': 1024,
                        'nomic-embed-text': 768,
                        'orca': 3072
                    }
                    
                    # Setze die richtige Dimension für das Modell
                    model_dim = model_dimensions.get(ollama_model, fallback_dimension)
                    logger.info(f"Verwende Dimension {model_dim} für Modell {ollama_model}")
                    
                    self.embedding_function = OllamaEmbeddingFunction(
                        base_url=ollama_url, 
                        model=ollama_model,
                        fallback_dimension=model_dim
                    )
                    logger.info(f"Ollama-Embedding-Funktion initialisiert mit Modell {ollama_model}")
                    
                except ImportError:
                    logger.warning("OllamaEmbeddingFunction nicht verfügbar, verwende Standard-Embedding-Funktion")
                    self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
                    
            elif embedding_function_name == 'openai':
                openai_api_key = config_manager.get('OPENAI_API_KEY', '')
                if openai_api_key:
                    self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                        api_key=openai_api_key,
                        model_name="text-embedding-ada-002"
                    )
                    logger.info("OpenAI-Embedding-Funktion initialisiert")
                else:
                    logger.warning("OpenAI API-Schlüssel fehlt, verwende Standard-Embedding-Funktion")
                    self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
                    
            elif embedding_function_name == 'huggingface':
                huggingface_api_key = config_manager.get('HUGGINGFACE_API_KEY', '')
                if huggingface_api_key:
                    self.embedding_function = embedding_functions.HuggingFaceEmbeddingFunction(
                        api_key=huggingface_api_key,
                        model_name="sentence-transformers/all-mpnet-base-v2"
                    )
                    logger.info("HuggingFace-Embedding-Funktion initialisiert")
                else:
                    logger.warning("HuggingFace API-Schlüssel fehlt, verwende Standard-Embedding-Funktion")
                    self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
            else:
                # Fallback zur lokalen Embedding-Funktion
                logger.warning(f"Unbekannte Embedding-Funktion: {embedding_function_name}, verwende Standard")
                self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
                
        except Exception as e:
            logger.error(f"Fehler beim Initialisieren der Embedding-Funktion: {e}")
            logger.warning("Verwende Standard-Embedding-Funktion als Fallback")
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
    
    def _init_client(self, max_retries: int = 3, retry_delay: float = 2.0):
        """
        Initialisiert den ChromaDB-Client mit Retry-Logik
        
        Args:
            max_retries: Maximale Anzahl von Verbindungsversuchen
            retry_delay: Verzögerung zwischen Versuchen in Sekunden
        """
        for attempt in range(max_retries):
            try:
                with _db_lock:
                    self.client = chromadb.PersistentClient(
                        path=self.persist_dir,
                        settings=Settings(
                            allow_reset=True,  # Nur für Entwicklung
                            anonymized_telemetry=False
                        )
                    )
                logger.info(f"ChromaDB verbunden unter {self.persist_dir}")
                return
            except Exception as e:
                logger.warning(f"ChromaDB-Verbindungsversuch {attempt+1} fehlgeschlagen: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponentielles Backoff
                else:
                    logger.error(f"Verbindung zu ChromaDB nach {max_retries} Versuchen fehlgeschlagen")
                    self.client = None
                    raise
    
    def ensure_client(self):
        """Stellt sicher, dass der ChromaDB-Client initialisiert ist"""
        with _db_lock:
            if self.client is None:
                self._init_client()
    
    def get_or_create_collection(self, collection_name: str):
        """
        Holt oder erstellt eine Kollektion mit korrekter Fehlerbehandlung und
        Korrektur von Dimensionsfehlern
        
        Args:
            collection_name: Name der Kollektion
            
        Returns:
            Collection: ChromaDB-Kollektion
            
        Raises:
            APIError: Wenn die Kollektion nicht erstellt oder abgerufen werden kann
        """
        self.ensure_client()
        
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                with _db_lock:
                    # Prüfe, ob Kollektion bereits existiert
                    collections = self.client.list_collections()
                    if collection_name in [c.name for c in collections]:
                        try:
                            coll = self.client.get_collection(
                                name=collection_name, 
                                embedding_function=self.embedding_function
                            )
                            
                            # Prüfe Kollektion mit einfacher Abfrage
                            try:
                                test_result = coll.query(
                                    query_texts=["test dimension check"], 
                                    n_results=1
                                )
                                logger.info(f"Kollektion {collection_name} erfolgreich abgerufen")
                                return coll
                            except Exception as dim_err:
                                # Prüfe, ob der Fehler mit Dimensionen zusammenhängt
                                if "dimension" in str(dim_err).lower() or "shape" in str(dim_err).lower():
                                    logger.warning(f"Dimensionsfehler in Kollektion {collection_name}, wird neu erstellt")
                                    
                                    # Hole Dokumente vor dem Löschen
                                    all_docs = None
                                    try:
                                        all_docs = coll.get(include=["documents", "metadatas"])
                                        logger.info(f"{len(all_docs['ids'])} Dokumente für Migration abgerufen")
                                    except Exception as get_err:
                                        logger.error(f"Dokumente für Migration konnten nicht abgerufen werden: {get_err}")
                                    
                                    # Lösche und erstelle Kollektion neu
                                    self.client.delete_collection(collection_name)
                                    new_coll = self.client.create_collection(
                                        name=collection_name, 
                                        embedding_function=self.embedding_function
                                    )
                                    
                                    # Migriere Dokumente, falls vorhanden
                                    if all_docs and all_docs['ids'] and len(all_docs['ids']) > 0:
                                        self._migrate_documents(new_coll, all_docs)
                                    
                                    return new_coll
                                else:
                                    # Anderer Fehler, nicht mit Dimensionen zusammenhängend
                                    raise
                        except Exception as e:
                            logger.error(f"Fehler beim Zugriff auf Kollektion {collection_name}: {e}")
                            raise
                    else:
                        # Erstelle neue Kollektion
                        return self.client.create_collection(
                            name=collection_name, 
                            embedding_function=self.embedding_function
                        )
            except Exception as e:
                logger.error(f"Fehler beim Holen/Erstellen der Kollektion {collection_name} (Versuch {attempt+1}): {e}")
                
                # Warte vor dem nächsten Versuch (außer beim letzten Versuch)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponentielles Backoff
        
        # Wenn wir hier ankommen, sind alle Versuche fehlgeschlagen
        raise APIError(f"Kollektion {collection_name} konnte nach {max_retries} Versuchen nicht erstellt werden", 500)
    
    def _migrate_documents(self, collection, all_docs):
        """
        Migriert Dokumente in eine neue Kollektion
        
        Args:
            collection: Zielkollektion
            all_docs: Quell-Dokumente
        """
        try:
            # Verarbeitung in Batches zu je 100
            batch_size = 100
            total_docs = len(all_docs['ids'])
            
            for i in range(0, total_docs, batch_size):
                end_idx = min(i + batch_size, total_docs)
                batch_ids = all_docs['ids'][i:end_idx]
                batch_docs = all_docs['documents'][i:end_idx]
                batch_meta = all_docs['metadatas'][i:end_idx] if 'metadatas' in all_docs else None
                
                # Batch zur neuen Kollektion hinzufügen
                if batch_meta:
                    collection.add(
                        ids=batch_ids,
                        documents=batch_docs,
                        metadatas=batch_meta
                    )
                else:
                    collection.add(
                        ids=batch_ids,
                        documents=batch_docs
                    )
                
                logger.info(f"Batch {i//batch_size + 1} mit {len(batch_ids)} Dokumenten migriert")
            
            logger.info(f"{total_docs} Dokumente erfolgreich in neue Kollektion migriert")
            
        except Exception as e:
            logger.error(f"Fehler bei der Dokumentmigration: {e}")
    
    def store_document_chunks(self, document_id: str, chunks: List[Dict[str, Any]], 
                              metadata: Dict[str, Any]) -> bool:
        """
        Speichert Dokumentchunks in der Vektordatenbank mit korrekter Transaktionsbehandlung
        
        Args:
            document_id: Eindeutige ID des Dokuments
            chunks: Liste von Textchunks mit Seitenzuweisung
            metadata: Dokumentmetadaten
            
        Returns:
            bool: Erfolgsstatus
        """
        if not chunks or len(chunks) == 0:
            logger.warning(f"Keine Chunks für Dokument {document_id} bereitgestellt")
            return False
        
        try:
            # Benutzerspezifische Kollektion
            user_id = metadata.get('user_id', 'default_user')
            collection = self.get_or_create_collection(f"user_{user_id}_documents")
            
            # Formatiere Metadaten für ChromaDB
            formatted_metadata = self._format_metadata_for_chroma(metadata)
            
            # Füge document_id zu Metadaten hinzu
            formatted_metadata["document_id"] = document_id
            
            # Bereite Chunk-IDs, Texte und Metadaten vor
            chunk_ids = []
            chunk_texts = []
            chunk_metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                chunk_ids.append(chunk_id)
                
                # Extrahiere Text aus dem Chunk
                if isinstance(chunk, dict):
                    chunk_text = chunk.get('text', '')
                    page_number = chunk.get('page_number')
                else:
                    # Fallback für einfache Textchunks
                    chunk_text = chunk
                    page_number = None
                
                # Überspringe leere Chunks
                if not chunk_text.strip():
                    continue
                    
                chunk_texts.append(chunk_text)
                
                # Erstelle Metadaten für diesen Chunk
                chunk_metadata = formatted_metadata.copy()
                chunk_metadata["chunk_index"] = str(i)
                chunk_metadata["chunk_count"] = str(len(chunks))
                
                # Füge Seitennummer hinzu, falls verfügbar
                if page_number:
                    chunk_metadata["page"] = str(page_number)
                
                chunk_metadatas.append(chunk_metadata)
            
            with _db_lock:
                # Lösche alle existierenden Chunks für dieses Dokument
                try:
                    existing_chunks = collection.get(
                        where={"document_id": document_id}
                    )
                    
                    if existing_chunks and existing_chunks["ids"]:
                        logger.info(f"Lösche {len(existing_chunks['ids'])} existierende Chunks für Dokument {document_id}")
                        collection.delete(
                            where={"document_id": document_id}
                        )
                except Exception as e:
                    logger.warning(f"Fehler beim Löschen existierender Chunks: {e}")
                
                # Füge Chunks in Batches hinzu, um Timeouts zu vermeiden
                BATCH_SIZE = 50
                for i in range(0, len(chunk_ids), BATCH_SIZE):
                    end_i = min(i + BATCH_SIZE, len(chunk_ids))
                    
                    batch_ids = chunk_ids[i:end_i]
                    batch_texts = chunk_texts[i:end_i]
                    batch_metadatas = chunk_metadatas[i:end_i]
                        
                    try:
                        collection.add(
                            ids=batch_ids,
                            documents=batch_texts,
                            metadatas=batch_metadatas
                        )
                        logger.info(f"Batch {i//BATCH_SIZE + 1} mit {len(batch_ids)} Chunks hinzugefügt")
                    except Exception as e:
                        logger.error(f"Fehler beim Hinzufügen von Chunk-Batch: {e}")
                        # Mit nächstem Batch fortfahren, anstatt komplett zu fehlschlagen
                
                # Leere den Cache für Anfragen, die dieses Dokument betreffen könnten
                self._clear_search_cache_for_document(document_id)
            
            logger.info(f"{len(chunk_ids)} Chunks für Dokument {document_id} erfolgreich gespeichert")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern von Dokumentchunks: {e}")
            return False
    
    def _format_metadata_for_chroma(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Formatiert Metadaten für ChromaDB
        
        Args:
            metadata: Rohe Metadaten
            
        Returns:
            dict: Formatierte Metadaten für ChromaDB
        """
        formatted = {}
        for key, value in metadata.items():
            if isinstance(value, list):
                # Konvertiere Listen in kommagetrennte Strings
                formatted[key] = ", ".join(str(item) for item in value)
            elif value is None:
                # Ersetze None-Werte durch leere Strings
                formatted[key] = ""
            else:
                # Konvertiere andere Werte in Strings
                formatted[key] = str(value)
        return formatted
    
    def _clear_search_cache_for_document(self, document_id: str):
        """
        Leert den Cache für Anfragen, die ein bestimmtes Dokument betreffen könnten
        
        Args:
            document_id: Dokument-ID
        """
        with self._cache_lock:
            # Entferne alle Cache-Einträge, in deren Schlüssel document_id vorkommt
            # oder die dieses Dokument in den Ergebnissen enthalten
            keys_to_remove = []
            
            for key, cached_item in self._search_cache.items():
                # Prüfe, ob document_id im Schlüssel enthalten ist
                if document_id in key:
                    keys_to_remove.append(key)
                    continue
                
                # Prüfe, ob document_id in den Ergebnissen enthalten ist
                results = cached_item.get('results', [])
                for result in results:
                    if result.get('document_id') == document_id or document_id in str(result.get('metadata', {})):
                        keys_to_remove.append(key)
                        break
            
            # Entferne alle gefundenen Schlüssel
            for key in keys_to_remove:
                self._search_cache.pop(key, None)
            
            logger.debug(f"{len(keys_to_remove)} Cache-Einträge für Dokument {document_id} gelöscht")
    
    def search_documents(
        self, 
        query: str, 
        user_id: str = "default_user", 
        filters: Optional[Dict[str, Any]] = None, 
        n_results: int = 5, 
        include_metadata: bool = True,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Sucht nach relevanten Dokumentchunks basierend auf einer Anfrage mit Caching
        
        Args:
            query: Suchanfrage
            user_id: Benutzer-ID
            filters: Filterkriterien (z.B. spezifische Dokumente)
            n_results: Anzahl der Ergebnisse
            include_metadata: Metadaten einschließen
            use_cache: Cache verwenden
            
        Returns:
            list: Liste relevanter Chunks mit Seitennummern
        """
        self.ensure_client()
        
        # Erstelle Cache-Schlüssel aus allen Parametern
        cache_key = f"{user_id}:{query}:{json.dumps(filters) if filters else 'None'}:{n_results}:{include_metadata}"
        
        # Prüfe Cache zuerst
        if use_cache:
            with self._cache_lock:
                if cache_key in self._search_cache:
                    cached_result = self._search_cache[cache_key]
                    # Nur Cache verwenden, wenn Ergebnis weniger als 5 Minuten alt ist
                    if time.time() - cached_result['timestamp'] < self._cache_ttl:
                        logger.info(f"Verwende Cache-Ergebnisse für Anfrage '{query}'")
                        return cached_result['results']
        
        try:
            # Benutzerspezifische Kollektion
            collection_name = f"user_{user_id}_documents"
            
            # Prüfe, ob Kollektion existiert
            with _db_lock:
                collections = self.client.list_collections()
                if collection_name not in [c.name for c in collections]:
                    logger.warning(f"Kollektion {collection_name} existiert nicht")
                    return []
                
                collection = self.client.get_collection(name=collection_name, embedding_function=self.embedding_function)
            
            # Erstelle Where-Klausel für Filter
            where_clause = {}
            if filters:
                if 'document_ids' in filters and filters['document_ids']:
                    where_clause["document_id"] = {"$in": filters['document_ids']}
            
            # Führe die Suche durch
            with _db_lock:
                results = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_clause,
                    include=["documents", "metadatas", "distances"] if include_metadata else ["documents"]
                )
            
            # Formatiere Ergebnisse
            formatted_results = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    result_item = {
                        "text": doc,
                        "relevance": 1.0 - min(results['distances'][0][i] / 2.0, 0.99) if 'distances' in results else None
                    }
                    
                    # Füge Metadaten hinzu
                    if include_metadata and 'metadatas' in results and results['metadatas'][0]:
                        metadata = results['metadatas'][0][i]
                        
                        # Versuche, Autoren aus JSON-String zu parsen
                        if 'authors' in metadata and metadata['authors']:
                            try:
                                authors = json.loads(metadata['authors'])
                            except json.JSONDecodeError:
                                logger.warning(f"JSON-Parsing für Autoren fehlgeschlagen: {metadata['authors']}")
                                authors = []
                            except Exception:
                                # Behandle Autorenstring direkt
                                authors = metadata['authors'].split(', ')
                        else:
                            authors = []
                        
                        # Formatiere Quellenangabe
                        source = ""
                        if metadata.get('title'):
                            if authors:
                                # Erster Autor mit et al. für mehrere Autoren
                                if isinstance(authors, list) and len(authors) > 0:
                                    if isinstance(authors[0], dict) and 'name' in authors[0]:
                                        first_author = authors[0]['name']
                                    else:
                                        first_author = str(authors[0])
                                else:
                                    first_author = str(authors)
                                    
                                if ',' in first_author:
                                    first_author = first_author.split(',')[0].strip()
                                    
                                author_text = first_author
                                if isinstance(authors, list) and len(authors) > 1:
                                    author_text += " et al."
                                
                                # Extrahiere Jahr aus Datum
                                year = ""
                                if metadata.get('publicationDate'):
                                    year_match = re.search(r'(\d{4})', metadata.get('publicationDate', ''))
                                    if year_match:
                                        year = year_match.group(1)
                                
                                source = f"{author_text} ({year})"
                                
                                # Füge Seitennummer hinzu, falls verfügbar
                                if metadata.get('page'):
                                    source += f", S. {metadata.get('page')}"
                            else:
                                source = metadata.get('title')
                        
                        result_item["source"] = source
                        result_item["document_id"] = metadata.get('document_id')
                        result_item["metadata"] = metadata
                    
                    formatted_results.append(result_item)
            
            # Cache die Ergebnisse
            if use_cache:
                with self._cache_lock:
                    self._search_cache[cache_key] = {
                        'results': formatted_results,
                        'timestamp': time.time()
                    }
                    
                    # Begrenze Cache-Größe (behalte die neuesten 100 Anfragen)
                    if len(self._search_cache) > self._max_cache_size:
                        oldest_key = min(self._search_cache.keys(), 
                                       key=lambda k: self._search_cache[k]['timestamp'])
                        self._search_cache.pop(oldest_key)
            
            logger.info(f"Anfrage '{query}' ergab {len(formatted_results)} Ergebnisse")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Fehler bei der Dokumentsuche: {e}")
            return []
    
    def delete_document(self, document_id: str, user_id: str = "default_user") -> bool:
        """
        Löscht alle Chunks eines Dokuments
        
        Args:
            document_id: ID des zu löschenden Dokuments
            user_id: Benutzer-ID
            
        Returns:
            bool: Erfolgsstatus
        """
        self.ensure_client()
        
        try:
            collection_name = f"user_{user_id}_documents"
            
            with _db_lock:
                # Prüfe, ob Kollektion existiert
                collections = self.client.list_collections()
                if collection_name not in [c.name for c in collections]:
                    logger.warning(f"Kollektion {collection_name} existiert nicht")
                    return True  # Nichts zu löschen
                
                collection = self.client.get_collection(name=collection_name, embedding_function=self.embedding_function)
                
                # Finde IDs der zu löschenden Chunks
                results = collection.get(
                    where={"document_id": document_id}
                )
                
                if results and results['ids']:
                    # Lösche Chunks in Batches, um Timeouts zu vermeiden
                    chunk_ids = results['ids']
                    for i in range(0, len(chunk_ids), 100):
                        batch_ids = chunk_ids[i:i+100]
                        collection.delete(ids=batch_ids)
                    
                    logger.info(f"{len(results['ids'])} Chunks für Dokument {document_id} gelöscht")
                    
                    # Leere alle Cache-Einträge, die dieses Dokument betreffen könnten
                    self._clear_search_cache_for_document(document_id)
                    
                    return True
                else:
                    logger.info(f"Keine Chunks für Dokument {document_id} gefunden")
                    return True
                
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Dokuments: {e}")
            return False
    
    def clear_cache(self):
        """Leert den gesamten Suchcache"""
        with self._cache_lock:
            self._search_cache.clear()
            logger.debug("Suchcache geleert")

def get_vector_storage() -> VectorStorage:
    """
    Holt die Singleton-Instanz der Vektordatenbank-Schnittstelle
    
    Returns:
        VectorStorage: Vektordatenbank-Schnittstelle
    """
    global _vector_storage
    
    if _vector_storage is None:
        _vector_storage = VectorStorage()
    
    return _vector_storage

# Exportiere Funktionen für einfacheren Zugriff in Altcode
def store_document_chunks(document_id, chunks, metadata):
    """Legacy-Funktion für Kompatibilität"""
    return get_vector_storage().store_document_chunks(document_id, chunks, metadata)

def search_documents(query, user_id="default_user", filters=None, n_results=5, include_metadata=True):
    """Legacy-Funktion für Kompatibilität"""
    return get_vector_storage().search_documents(query, user_id, filters, n_results, include_metadata)

def delete_document(document_id, user_id="default_user"):
    """Legacy-Funktion für Kompatibilität"""
    return get_vector_storage().delete_document(document_id, user_id)