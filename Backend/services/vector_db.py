# Backend/services/vector_db.py
import os
import chromadb
import logging
import json
import uuid
import re
import time
from typing import List, Dict, Any, Optional, Union
from chromadb.config import Settings
from chromadb.utils import embedding_functions
try:
    from services.ollama_embeddings import OllamaEmbeddingFunction
except ImportError:
    # Handle different import paths (e.g., when running from another directory)
    try:
        from .ollama_embeddings import OllamaEmbeddingFunction
    except ImportError:
        OllamaEmbeddingFunction = None

# Configure logging
logger = logging.getLogger(__name__)

# Path to Chroma directory
CHROMA_PERSIST_DIR = os.environ.get('CHROMA_PERSIST_DIR', './data/chroma')

# Configure embedding function
EMBEDDING_FUNCTION_NAME = os.environ.get('EMBEDDING_FUNCTION', 'ollama')  # Default to Ollama
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY', '')

# Initialize embedding function based on configuration
ef = None
embedding_function_error = None

try:
    if EMBEDDING_FUNCTION_NAME == 'ollama' and OllamaEmbeddingFunction is not None:
        ollama_url = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434')
        ollama_model = os.environ.get('OLLAMA_MODEL', 'llama3')
        
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
        logger.info(f"Using dimension {model_dim} for model {ollama_model}")
        
        ef = OllamaEmbeddingFunction(
            base_url=ollama_url, 
            model=ollama_model,
            fallback_dimension=model_dim
        )
        logger.info(f"Using Ollama embedding function with model {ollama_model}")
    elif EMBEDDING_FUNCTION_NAME == 'openai' and OPENAI_API_KEY:
        ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name="text-embedding-ada-002"
        )
        logger.info("Using OpenAI embedding function")
    elif EMBEDDING_FUNCTION_NAME == 'huggingface' and HUGGINGFACE_API_KEY:
        ef = embedding_functions.HuggingFaceEmbeddingFunction(
            api_key=HUGGINGFACE_API_KEY,
            model_name="sentence-transformers/all-mpnet-base-v2"
        )
        logger.info("Using HuggingFace embedding function")
    else:
        # Default to the local embedding function (less powerful)
        logger.warning(f"Using default embedding function (less powerful)")
        ef = embedding_functions.DefaultEmbeddingFunction()
except Exception as e:
    embedding_function_error = str(e)
    logger.error(f"Error initializing embedding function: {str(e)}")
    logger.warning("Falling back to default embedding function")
    ef = embedding_functions.DefaultEmbeddingFunction()

# Initialize ChromaDB client with robust retry logic
def get_chroma_client(max_retries=3, retry_delay=2.0):
    """
    Get ChromaDB client with retry logic
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        ChromaDB client
        
    Raises:
        Exception if connection fails after all retries
    """
    for attempt in range(max_retries):
        try:
            client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIR,
                settings=Settings(
                    allow_reset=True,  # Only for development
                    anonymized_telemetry=False
                )
            )
            logger.info(f"ChromaDB connected at {CHROMA_PERSIST_DIR}")
            return client
        except Exception as e:
            logger.warning(f"ChromaDB connection attempt {attempt+1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"Failed to connect to ChromaDB after {max_retries} attempts")
                raise

try:
    client = get_chroma_client()
except Exception as e:
    logger.error(f"Fatal error connecting to ChromaDB: {str(e)}")
    # Create a placeholder client that will be reinitialized on first use
    client = None

def ensure_client():
    """Ensure ChromaDB client is initialized"""
    global client
    if client is None:
        try:
            client = get_chroma_client()
        except Exception as e:
            logger.error(f"Cannot initialize ChromaDB client: {str(e)}")
            raise

def get_or_create_collection(collection_name: str):
    """
    Get or create a collection with proper error handling
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Collection object
    
    Raises:
        Exception: If collection cannot be created or retrieved
    """
    ensure_client()
    
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # Check if collection already exists
            collections = client.list_collections()
            if collection_name in [c.name for c in collections]:
                coll = client.get_collection(name=collection_name, embedding_function=ef)
                
                # Spezieller Fix für den Dimensions-Mismatch
                try:
                    # Versuche eine kleine Abfrage um die Dimensionen zu überprüfen
                    test_result = coll.query(query_texts=["test"], n_results=1)
                    logger.info(f"Collection {collection_name} accessed successfully")
                    return coll
                except Exception as e:
                    if "dimension" in str(e).lower():
                        # Bei Dimensions-Fehler die Sammlung löschen und neu erstellen
                        logger.warning(f"Dimension mismatch in collection {collection_name}, recreating...")
                        client.delete_collection(collection_name)
                        # Collection neu erstellen mit aktuellem Embedding-Modell
                        return client.create_collection(name=collection_name, embedding_function=ef)
                    else:
                        # Andere Fehler weitergeben
                        raise
            else:
                # Create new collection
                return client.create_collection(name=collection_name, embedding_function=ef)
        except Exception as e:
            logger.error(f"Error getting/creating collection {collection_name} (attempt {attempt+1}): {str(e)}")
            
            # Wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
    
    # If we get here, all retries failed
    raise Exception(f"Failed to get or create collection {collection_name} after {max_retries} attempts")


def store_document_chunks(document_id, chunks, metadata):
    """
    Stores document chunks in the vector database with proper transaction handling
    
    Args:
        document_id: Unique ID of the document
        chunks: List of text chunks with page assignment
        metadata: Document metadata
    
    Returns:
        bool: Success status
    """
    if not chunks or len(chunks) == 0:
        logger.warning(f"No chunks provided for document {document_id}")
        return False
    
    try:
        # Get user-specific collection
        user_id = metadata.get('user_id', 'default_user')
        collection = get_or_create_collection(f"user_{user_id}_documents")
        
        # Format metadata for ChromaDB
        def format_metadata_for_chroma(meta_dict):
            formatted = {}
            for key, value in meta_dict.items():
                if isinstance(value, list):
                    # Convert lists to comma-separated string
                    formatted[key] = ", ".join(str(item) for item in value)
                elif value is None:
                    # Replace None values with empty strings
                    formatted[key] = ""
                else:
                    # Convert other values to strings
                    formatted[key] = str(value)
            return formatted
        
        # Format authors correctly
        processed_metadata = format_metadata_for_chroma(metadata)
        
        # Add document_id to metadata
        processed_metadata["document_id"] = document_id
        
        # Prepare chunk IDs, texts, and metadata
        chunk_ids = []
        chunk_texts = []
        chunk_metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            
            # Extract text from the chunk
            if isinstance(chunk, dict):
                chunk_text = chunk.get('text', '')
                page_number = chunk.get('page_number')
            else:
                # Fallback for simple text chunks
                chunk_text = chunk
                page_number = None
            
            # Skip empty chunks
            if not chunk_text.strip():
                continue
                
            chunk_texts.append(chunk_text)
            
            # Create metadata for this chunk
            chunk_metadata = processed_metadata.copy()
            chunk_metadata["chunk_index"] = str(i)
            chunk_metadata["chunk_count"] = str(len(chunks))
            
            # Add page number if available
            if page_number:
                chunk_metadata["page"] = str(page_number)
            
            chunk_metadatas.append(chunk_metadata)
        
        # Store the document ID we're going to process for later deletion if needed
        temp_id = f"temp_{document_id}_{uuid.uuid4()}"
        
        # Delete any existing chunks for this document
        try:
            existing_chunks = collection.get(
                where={"document_id": document_id}
            )
            
            if existing_chunks and existing_chunks["ids"]:
                logger.info(f"Deleting {len(existing_chunks['ids'])} existing chunks for document {document_id}")
                collection.delete(
                    where={"document_id": document_id}
                )
        except Exception as e:
            logger.warning(f"Error deleting existing chunks: {e}")
        
        # Add chunks in batches to avoid timeouts
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
                logger.info(f"Added batch {i//BATCH_SIZE + 1} with {len(batch_ids)} chunks")
            except Exception as e:
                logger.error(f"Error adding chunk batch: {e}")
                # Continue with next batch instead of failing completely
        
        logger.info(f"Successfully stored {len(chunk_ids)} chunks for document {document_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing document chunks: {str(e)}")
        return False


def search_documents(query: str, user_id: str = "default_user", 
                    filters: Optional[Dict[str, Any]] = None, 
                    n_results: int = 5, 
                    include_metadata: bool = True) -> List[Dict[str, Any]]:
    """
    Search for relevant document chunks based on a query with caching
    
    Args:
        query: Search query
        user_id: User ID
        filters: Filter criteria (e.g., specific documents)
        n_results: Number of results
        include_metadata: Include metadata
    
    Returns:
        list: List of relevant chunks with page numbers
    """
    ensure_client()
    
    # Simple in-memory query cache (in a real system, use Redis or similar)
    # Note: This is a module-level cache
    if not hasattr(search_documents, '_cache'):
        search_documents._cache = {}
    
    # Create cache key from all parameters
    cache_key = f"{user_id}:{query}:{json.dumps(filters) if filters else 'None'}:{n_results}:{include_metadata}"
    
    # Check cache first
    if cache_key in search_documents._cache:
        cached_result = search_documents._cache[cache_key]
        # Only use cache if result is less than 5 minutes old
        if time.time() - cached_result['timestamp'] < 300:
            logger.info(f"Using cached results for query '{query}'")
            return cached_result['results']
    
    try:
        # User-specific collection
        collection_name = f"user_{user_id}_documents"
        if collection_name not in [c.name for c in client.list_collections()]:
            logger.warning(f"Collection {collection_name} does not exist")
            return []
        
        collection = client.get_collection(name=collection_name, embedding_function=ef)
        
        # Create where clause for filters
        where_clause = {}
        if filters:
            if 'document_ids' in filters and filters['document_ids']:
                where_clause["document_id"] = {"$in": filters['document_ids']}
        
        # Perform the search
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause,
            include=["documents", "metadatas", "distances"] if include_metadata else ["documents"]
        )
        
        # Format results
        formatted_results = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                result_item = {
                    "text": doc,
                    "relevance": 1.0 - min(results['distances'][0][i] / 2.0, 0.99) if 'distances' in results else None
                }
                
                # Add metadata
                if include_metadata and 'metadatas' in results and results['metadatas'][0]:
                    metadata = results['metadatas'][0][i]
                    
                    # Parse authors from JSON string
                    if 'authors' in metadata and metadata['authors']:
                        try:
                            authors = json.loads(metadata['authors'])
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse authors JSON: {metadata['authors']}")
                            authors = []
                        except Exception:
                            # Handle author string directly
                            authors = metadata['authors'].split(', ')
                    else:
                        authors = []
                    
                    # Format source citation
                    source = ""
                    if metadata.get('title'):
                        if authors:
                            # First author with et al. for multiple authors
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
                            
                            # Extract year from date
                            year = ""
                            if metadata.get('publicationDate'):
                                year_match = re.search(r'(\d{4})', metadata.get('publicationDate', ''))
                                if year_match:
                                    year = year_match.group(1)
                            
                            source = f"{author_text} ({year})"
                            
                            # Add page number if available
                            if metadata.get('page'):
                                source += f", S. {metadata.get('page')}"
                        else:
                            source = metadata.get('title')
                    
                    result_item["source"] = source
                    result_item["document_id"] = metadata.get('document_id')
                    result_item["metadata"] = metadata
                
                formatted_results.append(result_item)
        
        # Cache the results
        search_documents._cache[cache_key] = {
            'results': formatted_results,
            'timestamp': time.time()
        }
        
        # Limit cache size (keep most recent 100 queries)
        if len(search_documents._cache) > 100:
            oldest_key = min(search_documents._cache.keys(), 
                            key=lambda k: search_documents._cache[k]['timestamp'])
            search_documents._cache.pop(oldest_key)
        
        logger.info(f"Query '{query}' returned {len(formatted_results)} results")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return []


def delete_document(document_id: str, user_id: str = "default_user") -> bool:
    """
    Delete all chunks of a document
    
    Args:
        document_id: ID of the document to delete
        user_id: User ID
    
    Returns:
        bool: Success status
    """
    ensure_client()
    
    try:
        collection_name = f"user_{user_id}_documents"
        if collection_name not in [c.name for c in client.list_collections()]:
            logger.warning(f"Collection {collection_name} does not exist")
            return True  # Nothing to delete
        
        collection = client.get_collection(name=collection_name, embedding_function=ef)
        
        # Find IDs of chunks to delete
        results = collection.get(
            where={"document_id": document_id}
        )
        
        if results and results['ids']:
            # Delete chunks in batches to prevent timeouts
            chunk_ids = results['ids']
            for i in range(0, len(chunk_ids), 100):
                batch_ids = chunk_ids[i:i+100]
                collection.delete(ids=batch_ids)
            
            logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            
            # Clear any cached results that might include this document
            if hasattr(search_documents, '_cache'):
                search_documents._cache.clear()
            
            return True
        else:
            logger.info(f"No chunks found for document {document_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return False