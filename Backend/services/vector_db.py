# Backend/services/vector_db.py
import os
import chromadb
import logging
import json
import uuid
from chromadb.config import Settings
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# Pfad zum Chroma-Verzeichnis
CHROMA_PERSIST_DIR = os.environ.get('CHROMA_PERSIST_DIR', './data/chroma')

# Einbettungsfunktion konfigurieren
EMBEDDING_FUNCTION_NAME = os.environ.get('EMBEDDING_FUNCTION', 'openai')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY', '')

# Defaultmäßig OpenAI-Embeddings verwenden, Fallback auf HuggingFace
if EMBEDDING_FUNCTION_NAME == 'openai' and OPENAI_API_KEY:
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-ada-002"
    )
elif EMBEDDING_FUNCTION_NAME == 'huggingface' and HUGGINGFACE_API_KEY:
    ef = embedding_functions.HuggingFaceEmbeddingFunction(
        api_key=HUGGINGFACE_API_KEY,
        model_name="sentence-transformers/all-mpnet-base-v2"
    )
else:
    # Default ist die lokale Einbettungsfunktion (weniger leistungsfähig)
    ef = embedding_functions.DefaultEmbeddingFunction()

# ChromaDB Client initialisieren
try:
    client = chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=Settings(
            allow_reset=True,  # Nur für Entwicklung
            anonymized_telemetry=False
        )
    )
    logger.info(f"ChromaDB connected at {CHROMA_PERSIST_DIR}")
except Exception as e:
    logger.error(f"Failed to connect to ChromaDB: {e}")
    raise


def get_or_create_collection(collection_name):
    """
    Collection abrufen oder erstellen
    """
    try:
        # Prüfen, ob Collection bereits existiert
        collections = client.list_collections()
        if collection_name in [c.name for c in collections]:
            return client.get_collection(name=collection_name, embedding_function=ef)
        else:
            # Neue Collection erstellen
            return client.create_collection(name=collection_name, embedding_function=ef)
    except Exception as e:
        logger.error(f"Error getting/creating collection {collection_name}: {e}")
        raise


def store_document_chunks(document_id, chunks, metadata):
    """
    Speichert die Chunks eines Dokuments in der Vektordatenbank mit Seitenzahlen
    
    Args:
        document_id (str): Eindeutige ID des Dokuments
        chunks (list): Liste von Textabschnitten mit Seitenzuordnung
        metadata (dict): Metadaten des Dokuments
    
    Returns:
        bool: Erfolg der Speicherung
    """
    try:
        # Benutzer-spezifische Collection abrufen/erstellen
        user_id = metadata.get('user_id', 'default_user')
        collection = get_or_create_collection(f"user_{user_id}_documents")
        
        # Vorhandene Chunks für dieses Dokument entfernen (falls Update)
        existing_ids = collection.get(
            where={"document_id": document_id}
        )
        
        if existing_ids and existing_ids['ids']:
            collection.delete(ids=existing_ids['ids'])
            logger.info(f"Deleted {len(existing_ids['ids'])} existing chunks for document {document_id}")
        
        # Basis-Metadaten für alle Chunks vorbereiten
        authors_json = json.dumps(metadata.get('authors', []))
        base_metadata = {
            "document_id": document_id,
            "title": metadata.get('title', ''),
            "authors": authors_json,
            "type": metadata.get('type', 'other'),
            "publication_date": metadata.get('publicationDate', ''),
            "doi": metadata.get('doi', ''),
            "isbn": metadata.get('isbn', ''),
            "journal": metadata.get('journal', ''),
            "publisher": metadata.get('publisher', ''),
            # Weitere relevante Felder aus den Metadaten
            "volume": metadata.get('volume', ''),
            "issue": metadata.get('issue', ''),
            "pages": metadata.get('pages', ''),
            "publisherLocation": metadata.get('publisherLocation', ''),
            "url": metadata.get('url', ''),
            "abstract": metadata.get('abstract', '')
        }
        
        # Chunk-IDs, Texte und Metadaten vorbereiten
        chunk_ids = []
        chunk_texts = []
        chunk_metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            
            # Text aus dem Chunk extrahieren
            if isinstance(chunk, dict):
                chunk_text = chunk.get('text', '')
                page_number = chunk.get('page_number')
            else:
                # Fallback für einfache Textchunks
                chunk_text = chunk
                page_number = None
            
            chunk_texts.append(chunk_text)
            
            # Metadaten pro Chunk mit Position im Dokument und Seitenzahl
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["chunk_count"] = len(chunks)
            
            # Seitennummer hinzufügen
            if page_number:
                chunk_metadata["page"] = str(page_number)
            
            chunk_metadatas.append(chunk_metadata)
        
        # Chunks in der Collection speichern (batch-weise)
        batch_size = 100  # Batches von maximal 100 Chunks
        for i in range(0, len(chunk_ids), batch_size):
            end_idx = min(i + batch_size, len(chunk_ids))
            collection.add(
                ids=chunk_ids[i:end_idx],
                documents=chunk_texts[i:end_idx],
                metadatas=chunk_metadatas[i:end_idx]
            )
        
        logger.info(f"Stored {len(chunks)} chunks for document {document_id} with page numbers")
        return True
        
    except Exception as e:
        logger.error(f"Error storing document chunks: {e}")
        return False


def search_documents(query, user_id="default_user", filters=None, n_results=5, include_metadata=True):
    """
    Sucht nach relevanten Dokumenten-Chunks basierend auf einer Anfrage
    
    Args:
        query (str): Suchanfrage
        user_id (str): ID des Benutzers
        filters (dict): Filterkriterien (z.B. nur bestimmte Dokumente)
        n_results (int): Anzahl der Ergebnisse
        include_metadata (bool): Metadaten einschließen
    
    Returns:
        list: Liste der relevanten Chunks mit Seitenzahlen
    """
    try:
        # Benutzer-spezifische Collection abrufen
        collection_name = f"user_{user_id}_documents"
        if collection_name not in [c.name for c in client.list_collections()]:
            logger.warning(f"Collection {collection_name} does not exist")
            return []
        
        collection = client.get_collection(name=collection_name, embedding_function=ef)
        
        # Where-Klausel für Filter erstellen
        where_clause = {}
        if filters:
            if 'document_ids' in filters and filters['document_ids']:
                # Filter nach bestimmten Dokumenten
                where_clause["document_id"] = {"$in": filters['document_ids']}
        
        # Suche durchführen
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause if where_clause else None,
            include=["documents", "metadatas", "distances"] if include_metadata else ["documents"]
        )
        
        # Ergebnisse formatieren
        formatted_results = []
        if results and results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                result_item = {
                    "text": doc,
                    "relevance": 1.0 - min(results['distances'][0][i] / 2.0, 0.99) if 'distances' in results else None
                }
                
                # Metadaten hinzufügen
                if include_metadata and 'metadatas' in results and results['metadatas'][0]:
                    metadata = results['metadatas'][0][i]
                    
                    # Autoren aus JSON-String parsen
                    if 'authors' in metadata and metadata['authors']:
                        try:
                            authors = json.loads(metadata['authors'])
                        except:
                            authors = []
                    else:
                        authors = []
                    
                    # Quelle formatieren
                    source = ""
                    if metadata.get('title'):
                        if authors and len(authors) > 0:
                            # Ersten Autor mit et al. für mehrere Autoren
                            if len(authors) == 1:
                                author_text = authors[0].get('name', '')
                                if ',' in author_text:
                                    author_text = author_text.split(',')[0]
                            else:
                                first_author = authors[0].get('name', '')
                                if ',' in first_author:
                                    first_author = first_author.split(',')[0]
                                author_text = f"{first_author} et al."
                            
                            # Jahr aus Datum extrahieren
                            year = ""
                            if metadata.get('publication_date'):
                                year_match = re.search(r'(\d{4})', metadata.get('publication_date', ''))
                                if year_match:
                                    year = year_match.group(1)
                            
                            source = f"{author_text} ({year})"
                            
                            # Seitenzahl hinzufügen, wenn vorhanden
                            if metadata.get('page'):
                                source += f", S. {metadata.get('page')}"
                        else:
                            source = metadata.get('title')
                    
                    result_item["source"] = source
                    result_item["document_id"] = metadata.get('document_id')
                    result_item["metadata"] = metadata
                
                formatted_results.append(result_item)
        
        logger.info(f"Query '{query}' returned {len(formatted_results)} results")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return []


def delete_document(document_id, user_id="default_user"):
    """
    Löscht alle Chunks eines Dokuments
    
    Args:
        document_id (str): ID des zu löschenden Dokuments
        user_id (str): ID des Benutzers
    
    Returns:
        bool: Erfolg der Löschung
    """
    try:
        collection_name = f"user_{user_id}_documents"
        if collection_name not in [c.name for c in client.list_collections()]:
            logger.warning(f"Collection {collection_name} does not exist")
            return True  # Nichts zu löschen
        
        collection = client.get_collection(name=collection_name, embedding_function=ef)
        
        # IDs der zu löschenden Chunks finden
        results = collection.get(
            where={"document_id": document_id}
        )
        
        if results and results['ids']:
            # Chunks löschen
            collection.delete(ids=results['ids'])
            logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            return True
        else:
            logger.info(f"No chunks found for document {document_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return False