# services/vector_db.py
import chromadb
from chromadb.utils import embedding_functions
import os
import uuid
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Starte Chroma-Client
CHROMA_PATH = os.environ.get("CHROMA_DB_DIR", "./chromadb")
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Embedding-Methode (z. B. Ollama)
DEFAULT_EMBEDDING_FN = embedding_functions.DefaultEmbeddingFunction()


def get_or_create_collection(collection_name: str):
    """Erzeuge oder hole bestehende Collection"""
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=DEFAULT_EMBEDDING_FN
    )


def format_authors_for_citation(authors):
    if isinstance(authors, list):
        if len(authors) == 0:
            return "o. V."
        elif len(authors) == 1:
            return authors[0].split(',')[0]  # Nachname
        else:
            return authors[0].split(',')[0] + " et al."
    elif isinstance(authors, str):
        return authors.split(',')[0]
    return "o. V."


def store_document_chunks(document_id: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any]):
    """
    Speichert alle Chunks eines Dokuments in der Vektordatenbank mit vollständigen Metadaten.
    """
    user_id = metadata.get("user_id", "default_user")
    collection_name = f"user_{user_id}_documents"
    collection = get_or_create_collection(collection_name)

    if not chunks or len(chunks) == 0:
        raise ValueError("Keine Chunks zum Speichern vorhanden")

    logger.info(f"Speichere {len(chunks)} Chunks für Dokument {document_id} in Collection {collection_name}")

    documents = []
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "").strip()
        if not text:
            continue

        page_number = chunk.get("page_number", 1)

        # Zitier-Infos für spätere Anzeige erzeugen
        authors = metadata.get("authors", [])
        citation_author = format_authors_for_citation(authors)
        citation_year = metadata.get("publicationDate", "n.d.")[:4]
        citation = f"{citation_author} {citation_year}, S. {page_number}"

        full_metadata = {
            "user_id": user_id,
            "document_id": document_id,
            "page_number": page_number,
            "title": metadata.get("title", ""),
            "authors": authors,
            "type": metadata.get("type", "article"),
            "publicationDate": metadata.get("publicationDate", ""),
            "journal": metadata.get("journal", ""),
            "publisher": metadata.get("publisher", ""),
            "doi": metadata.get("doi", ""),
            "isbn": metadata.get("isbn", ""),
            "volume": metadata.get("volume", ""),
            "issue": metadata.get("issue", ""),
            "pages": metadata.get("pages", ""),
            "citation": citation  # Für direkte Anzeige im Chat
        }

        documents.append(text)
        metadatas.append(full_metadata)
        ids.append(f"{document_id}_{i}_{uuid.uuid4().hex[:8]}")

    if not documents:
        raise ValueError("Alle Chunks waren leer – nichts gespeichert")

    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    logger.info(f"{len(documents)} Chunks erfolgreich gespeichert")
    return {"stored": len(documents)}


def delete_document(document_id: str, user_id: str):
    """
    Entfernt alle Chunks eines Dokuments aus der Collection
    """
    collection_name = f"user_{user_id}_documents"
    collection = get_or_create_collection(collection_name)
    try:
        # Hole alle Einträge mit passender document_id
        results = collection.get(where={"document_id": document_id})
        if results and "ids" in results:
            collection.delete(ids=results["ids"])
            logger.info(f"Dokument {document_id} mit {len(results['ids'])} Chunks gelöscht")
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Dokuments {document_id}: {e}")


def search_documents(query: str, user_id: str, filters: Dict[str, Any] = None, n_results=5, include_metadata=True):
    """
    Durchsucht die Vektordatenbank für einen bestimmten User
    """
    collection_name = f"user_{user_id}_documents"
    collection = get_or_create_collection(collection_name)

    where_filter = filters or {}
    if "document_ids" in where_filter:
        where_filter = {
            "$and": [{"document_id": doc_id} for doc_id in where_filter["document_ids"]]
        }

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas"] if include_metadata else ["documents"]
    )

    formatted = []
    for i in range(len(results["documents"][0])):
        formatted.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i] if include_metadata else {},
            "source": results["metadatas"][0][i].get("citation", "") if include_metadata else ""
        })

    return formatted
