import os
import logging
import json
import chromadb
from chromadb.config import Settings
import uuid
import textwrap
import re

# Configure logging
logger = logging.getLogger(__name__)

class VectorService:
    """Service for handling vector database operations and LLM integration"""
    
    def __init__(self):
        # In a real app, this would connect to an actual LLM API like OpenAI
        self.llm_available = os.environ.get('OPENAI_API_KEY', '') != ''
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=os.environ.get(
                'CHROMA_PERSIST_DIRECTORY', 
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chroma_db')
            )
        ))
        
        # Create or get the collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="document_chunks",
            metadata={"hnsw:space": "cosine"}
        )
    
    def create_chunks(self, text, chunk_size=1000, chunk_overlap=200):
        """Split text into overlapping chunks"""
        chunks = []
        
        if not text or len(text.strip()) == 0:
            return chunks
        
        # Clean the text - remove multiple spaces and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split text into chunks
        start = 0
        while start < len(text):
            # Find the end of the chunk
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to find a natural break point (period followed by space)
            natural_break = text.rfind('. ', start, end)
            if natural_break != -1 and natural_break + 2 > start + chunk_size // 2:
                # If found a good break point, use it
                end = natural_break + 2
            else:
                # Otherwise, find the last space in the chunk
                last_space = text.rfind(' ', start, end)
                if last_space != -1:
                    end = last_space + 1
            
            chunks.append(text[start:end])
            start = end - chunk_overlap
        
        return chunks
    
    def store_chunks(self, chunks, document_id, metadata):
        """Store document chunks in the vector database"""
        if not chunks:
            logger.warning(f"No chunks to store for document ID: {document_id}")
            return
        
        # Prepare metadata as a dictionary
        meta_dict = {
            'document_id': document_id,
            'title': metadata.get('title', ''),
            'authors': metadata.get('authors', ''),
            'year': metadata.get('year', ''),
            'type': 'book' if metadata.get('isbn') else 'article',
        }
        
        # Add type-specific fields
        if meta_dict['type'] == 'article':
            meta_dict.update({
                'journal': metadata.get('journal', ''),
                'volume': metadata.get('volume', ''),
                'issue': metadata.get('issue', ''),
                'pages': metadata.get('pages', ''),
                'doi': metadata.get('doi', '')
            })
        else:
            meta_dict.update({
                'publisher': metadata.get('publisher', ''),
                'isbn': metadata.get('isbn', '')
            })
        
        # Convert metadata values to strings for ChromaDB compatibility
        for key, value in meta_dict.items():
            if not isinstance(value, str):
                meta_dict[key] = str(value)
        
        # Determine user email from document_id (in a real app, this would be stored in metadata)
        # For now, we'll use a placeholder
        meta_dict['user_email'] = 'user@example.com'
        
        # Store each chunk
        ids = []
        metadatas = []
        documents = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_{i}"
            
            # Add chunk-specific metadata
            chunk_meta = meta_dict.copy()
            chunk_meta['chunk_index'] = i
            chunk_meta['chunk_count'] = len(chunks)
            
            ids.append(chunk_id)
            metadatas.append(chunk_meta)
            documents.append(chunk)
        
        # Add chunks to the collection
        self.collection.add(
            ids=ids,
            metadatas=metadatas,
            documents=documents
        )
        
        logger.info(f"Stored {len(chunks)} chunks for document ID: {document_id}")
    
    def search(self, query, user_email, document_ids=None, limit=5):
        """Search for relevant document chunks"""
        # Prepare where clause for filtering
        where_clause = {"user_email": user_email}
        
        # If specific document IDs are provided, filter by them
        if document_ids and isinstance(document_ids, list) and document_ids:
            where_clause["document_id"] = {"$in": document_ids}
        
        # Perform the search
        results = self.collection.query(
            query_texts=[query],
            where=where_clause,
            n_results=limit
        )
        
        # Format the results
        formatted_results = []
        
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                
                # Extract page number or location if available
                page_info = self._extract_page_info(doc)
                
                formatted_results.append({
                    'document_id': metadata['document_id'],
                    'title': metadata['title'],
                    'authors': metadata['authors'],
                    'year': metadata['year'],
                    'type': metadata['type'],
                    'text': doc,
                    'page': page_info,
                    'metadata': metadata
                })
        
        return formatted_results
    
    def _extract_page_info(self, text):
        """Extract page number information from text if available"""
        # Look for common page patterns like "Page 42" or "p. 42"
        page_pattern = r'[Pp]age\s+(\d+)|[Pp]\.\s*(\d+)'
        match = re.search(page_pattern, text)
        
        if match:
            # Return the first non-None group
            for group in match.groups():
                if group:
                    return group
        
        return None
    
    def delete_document_chunks(self, document_id):
        """Delete all chunks for a document"""
        try:
            # Delete chunks where document_id matches
            self.collection.delete(
                where={"document_id": document_id}
            )
            logger.info(f"Deleted chunks for document ID: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting chunks for document ID {document_id}: {str(e)}")
            return False
    
    def generate_response_with_citations(self, query, search_results, citation_style='apa7'):
        """Generate a response with proper citations based on search results"""
        # If no search results or LLM not available, return a simple response
        if not search_results or not self.llm_available:
            return {
                'answer': 'I could not find enough information to answer your question.',
                'citations': [],
                'references': []
            }
        
        # In a real app, this would send the query and search results to an LLM API
        # For this prototype, we'll generate a simple answer with citations
        
        # Create a synthetic answer based on the first search result
        first_result = search_results[0]
        
        # Extract a relevant snippet from the text
        text_snippet = textwrap.shorten(
            first_result['text'], 
            width=200, 
            placeholder="..."
        )
        
        # Format the answer with citation
        authors_last_name = self._get_first_author_last_name(first_result['authors'])
        year = first_result['year']
        page = first_result.get('page', '')
        
        # Format in-text citation based on style
        if citation_style == 'apa7':
            citation = f"({authors_last_name}, {year}{', p. ' + page if page else ''})"
        elif citation_style == 'chicago18':
            citation = f"({authors_last_name} {year}{', ' + page if page else ''})"
        else:  # Harvard
            citation = f"({authors_last_name}, {year}{': ' + page if page else ''})"
        
        answer = f"{text_snippet} {citation}"
        
        # Create citations list
        citations = []
        references = []
        
        # Add a citation for each used search result
        for result in search_results:
            citation_id = str(uuid.uuid4())
            
            citations.append({
                'id': citation_id,
                'document_id': result['document_id'],
                'authors': result['authors'],
                'year': result['year'],
                'title': result['title'],
                'page': result.get('page', '')
            })
            
            # Generate reference based on style and document type
            reference = self._format_reference(result, citation_style)
            references.append(reference)
        
        return {
            'answer': answer,
            'citations': citations,
            'references': references
        }
    
    def _get_first_author_last_name(self, authors_string):
        """Extract the last name of the first author"""
        if not authors_string:
            return "Unknown"
        
        # Split authors by semicolon
        authors = authors_string.split(';')
        first_author = authors[0].strip()
        
        # If format is "Last, First"
        if ',' in first_author:
            return first_author.split(',')[0].strip()
        
        # If format is "First Last"
        return first_author.split()[-1]
    
    def _format_reference(self, result, citation_style):
        """Format a reference based on citation style and document type"""
        authors = result['authors']
        year = result['year']
        title = result['title']
        
        if result['type'] == 'article':
            journal = result['metadata'].get('journal', '')
            volume = result['metadata'].get('volume', '')
            issue = result['metadata'].get('issue', '')
            pages = result['metadata'].get('pages', '')
            doi = result['metadata'].get('doi', '')
            
            if citation_style == 'apa7':
                reference = f"{authors} ({year}). {title}. "
                if journal:
                    reference += f"{journal}"
                    if volume:
                        reference += f", {volume}"
                        if issue:
                            reference += f"({issue})"
                    if pages:
                        reference += f", {pages}"
                    reference += "."
                if doi:
                    reference += f" https://doi.org/{doi}"
            
            elif citation_style == 'chicago18':
                reference = f"{authors}. \"{title}.\" "
                if journal:
                    reference += f"{journal} "
                    if volume:
                        reference += f"{volume}"
                        if issue:
                            reference += f", no. {issue}"
                    if year:
                        reference += f" ({year})"
                    if pages:
                        reference += f": {pages}"
                    reference += "."
            
            else:  # Harvard
                reference = f"{authors}, {year}. {title}. "
                if journal:
                    reference += f"{journal}"
                    if volume:
                        reference += f", {volume}"
                        if issue:
                            reference += f"({issue})"
                    if pages:
                        reference += f", pp. {pages}"
                    reference += "."
        
        else:  # Book
            publisher = result['metadata'].get('publisher', '')
            isbn = result['metadata'].get('isbn', '')
            
            if citation_style == 'apa7':
                reference = f"{authors} ({year}). {title}. "
                if publisher:
                    reference += f"{publisher}."
                if isbn:
                    reference += f" ISBN: {isbn}"
            
            elif citation_style == 'chicago18':
                reference = f"{authors}. {title}. "
                if publisher:
                    reference += f"{publisher}, {year}."
            
            else:  # Harvard
                reference = f"{authors}, {year}. {title}. "
                if publisher:
                    reference += f"{publisher}."
        
        return reference
