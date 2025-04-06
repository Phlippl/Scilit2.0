from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import uuid
import spacy
import chromadb
from chromadb.config import Settings
from werkzeug.utils import secure_filename
import PyPDF2
import json
from datetime import datetime
import re
import requests
from pathlib import Path
import shutil

# Configuration
UPLOAD_FOLDER = Path('./uploads')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB max upload size

# Create upload directory if it doesn't exist
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Initialize spaCy
try:
    nlp = spacy.load("en_core_web_sm")
    print("Loaded spaCy model: en_core_web_sm")
except OSError:
    try:
        nlp = spacy.load("de_core_news_sm")
        print("Loaded spaCy model: de_core_news_sm")
    except OSError:
        print("Downloading spaCy model...")
        spacy.cli.download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

# Create collections for different document types
papers_collection = chroma_client.get_or_create_collection(name="academic_papers")
books_collection = chroma_client.get_or_create_collection(name="books")

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration from environment variables
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', './uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 20 * 1024 * 1024))
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(documents_bp)
    app.register_blueprint(metadata_bp)
    app.register_blueprint(query_bp)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Ensure Chroma DB directory exists
    chroma_dir = os.environ.get('CHROMA_PERSIST_DIR', './data/chroma')
    os.makedirs(chroma_dir, exist_ok=True)
    
    # Root route for health check
    @app.route('/')
    def health_check():
        return {'status': 'ok', 'version': '1.0.0'}
    
    return app
    
    # Helper functions
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def extract_text_from_pdf(file_path):
        """Extract text from a PDF file."""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
        return text

    def extract_doi(text):
        """Extract DOI from text using regex."""
        doi_pattern = r'\b(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\b'
        match = re.search(doi_pattern, text)
        return match.group(1) if match else None

    def extract_isbn(text):
        """Extract ISBN from text using regex."""
        isbn_pattern = r'ISBN(?:-13)?:?\s*((?:\d[-\s]?){13}|\d{13})'
        match = re.search(isbn_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).replace('-', '').replace(' ', '')
        
        # Try ISBN-10
        isbn_pattern = r'ISBN(?:-10)?:?\s*((?:\d[-\s]?){10}|\d{10})'
        match = re.search(isbn_pattern, text, re.IGNORECASE)
        return match.group(1).replace('-', '').replace(' ', '') if match else None

    def fetch_metadata_from_crossref(doi):
        """Fetch metadata from CrossRef API using DOI."""
        if not doi:
            return None
        
        try:
            url = f"https://api.crossref.org/works/{doi}"
            headers = {
                "User-Agent": "AcademicLiteratureAssistant/1.0 (mailto:your.email@example.com)"
            }
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json().get('message')
            return None
        except Exception as e:
            print(f"Error fetching CrossRef metadata: {e}")
            return None

    def chunk_text(text, chunk_size=1000, overlap=200):
        """
        Split text into chunks with overlap.
        
        Args:
            text (str): The text to chunk
            chunk_size (int): Target size of each chunk in characters
            overlap (int): Number of characters to overlap between chunks
            
        Returns:
            list: List of text chunks
        """
        if not text:
            return []
            
        # Process with spaCy to get sentence boundaries
        doc = nlp(text)
        sentences = list(doc.sents)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_text = sentence.text.strip()
            sentence_len = len(sentence_text)
            
            # If adding this sentence would exceed chunk size, 
            # store the current chunk and start a new one
            if current_size + sentence_len > chunk_size and current_size > 0:
                chunk_text = " ".join(current_chunk)
                chunks.append(chunk_text)
                
                # Create overlap by keeping some sentences from the end
                overlap_text = []
                overlap_size = 0
                
                # Work backwards through the current chunk to create overlap
                for s in reversed(current_chunk):
                    if overlap_size + len(s) <= overlap:
                        overlap_text.insert(0, s)
                        overlap_size += len(s) + 1  # +1 for the space
                    else:
                        break
                        
                # Start new chunk with overlap text
                current_chunk = overlap_text
                current_size = overlap_size
            
            # Add the current sentence to the chunk
            current_chunk.append(sentence_text)
            current_size += sentence_len + 1  # +1 for the space
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(chunk_text)
            
        return chunks

    def format_citation(metadata, citation_style="apa"):
        """
        Format citation based on metadata and style.
        
        Args:
            metadata (dict): Document metadata
            citation_style (str): Citation style (apa, chicago, harvard)
            
        Returns:
            str: Formatted citation
        """
        if not metadata:
            return ""
        
        # Extract common elements
        authors = metadata.get('authors', [])
        title = metadata.get('title', '')
        year = metadata.get('year', '')
        journal = metadata.get('journal', '')
        volume = metadata.get('volume', '')
        issue = metadata.get('issue', '')
        pages = metadata.get('pages', '')
        publisher = metadata.get('publisher', '')
        doi = metadata.get('doi', '')
        
        # Extract year from publication date if available
        if not year and 'publication_date' in metadata:
            match = re.search(r'(\d{4})', metadata['publication_date'])
            if match:
                year = match.group(1)
        
        # Format author names
        author_list = []
        for author in authors:
            if 'family' in author and 'given' in author:
                author_list.append(f"{author['family']}, {author['given']}")
            elif 'name' in author:
                author_list.append(author['name'])
        
        # Default to APA style
        if citation_style.lower() == "chicago":
            # Chicago 18th edition
            if not author_list:
                return f"{title}. {year}. {journal} {volume}({issue}): {pages}."
            
            authors_text = " and ".join(author_list) if len(author_list) <= 3 else f"{author_list[0]} et al."
            if journal:  # For journal article
                return f"{authors_text}. {year}. \"{title}.\" {journal} {volume}({issue}): {pages}."
            else:  # For book
                return f"{authors_text}. {year}. {title}. {publisher}."
                
        elif citation_style.lower() == "harvard":
            # Harvard style
            if not author_list:
                return f"{title} ({year}) {journal}, {volume}({issue}), pp. {pages}."
                
            authors_text = " and ".join(author_list) if len(author_list) <= 3 else f"{author_list[0]} et al."
            if journal:  # For journal article
                return f"{authors_text} ({year}) '{title}', {journal}, {volume}({issue}), pp. {pages}."
            else:  # For book
                return f"{authors_text} ({year}) {title}. {publisher}."
                
        else:  # APA 7th edition (default)
            if not author_list:
                return f"{title}. ({year}). {journal}, {volume}({issue}), {pages}. https://doi.org/{doi}"
                
            authors_text = ", ".join(author_list[:-1]) + " & " + author_list[-1] if len(author_list) > 1 else author_list[0]
            if len(author_list) > 7:
                authors_text = ", ".join(author_list[:6]) + "... " + author_list[-1]
                
            if journal:  # For journal article
                return f"{authors_text} ({year}). {title}. {journal}, {volume}({issue}), {pages}. https://doi.org/{doi}"
            else:  # For book
                return f"{authors_text} ({year}). {title}. {publisher}."

    # Register API routes
    @app.route('/api/documents', methods=['GET'])
    def list_documents():
        """List all processed documents."""
        try:
            documents = []
            
            # Get all JSON metadata files
            metadata_files = list(UPLOAD_FOLDER.glob("*.json"))
            
            for file in metadata_files:
                with open(file, 'r') as f:
                    metadata = json.load(f)
                    documents.append(metadata)
            
            return jsonify(sorted(documents, key=lambda x: x.get('upload_date', ''), reverse=True))
            
        except Exception as e:
            print(f"Error listing documents: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/documents/<document_id>', methods=['GET'])
    def get_document(document_id):
        """Get document details by ID."""
        try:
            # Find the metadata file
            metadata_files = list(UPLOAD_FOLDER.glob(f"{document_id}_*.json"))
            
            if not metadata_files:
                return jsonify({"error": "Document not found"}), 404
                
            with open(metadata_files[0], 'r') as f:
                metadata = json.load(f)
                
            return jsonify(metadata)
            
        except Exception as e:
            print(f"Error retrieving document {document_id}: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/documents', methods=['POST'])
    def save_document():
        """Handle document upload and processing."""
        if 'file' not in request.files and not request.form.get('data'):
            return jsonify({"error": "No file or data provided"}), 400
            
        # Extract metadata from form data
        metadata = {}
        if 'data' in request.form:
            try:
                metadata = json.loads(request.form.get('data', '{}'))
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data"}), 400
        
        # Generate document ID if not provided
        document_id = metadata.get('id', str(uuid.uuid4()))
        
        # Process PDF file if uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No selected file"}), 400
                
            if not allowed_file(file.filename):
                return jsonify({"error": "File type not allowed"}), 400
            
            # Save the uploaded file
            filename = secure_filename(file.filename)
            filepath = UPLOAD_FOLDER / f"{document_id}_{filename}"
            file.save(filepath)
            
            try:
                # Extract text from PDF
                extracted_text = extract_text_from_pdf(filepath)
                
                # Extract identifiers if not already provided
                if 'doi' not in metadata or not metadata['doi']:
                    metadata['doi'] = extract_doi(extracted_text)
                
                if 'isbn' not in metadata or not metadata['isbn']:
                    metadata['isbn'] = extract_isbn(extracted_text)
                
                # Fetch metadata from CrossRef if DOI is available and metadata incomplete
                if metadata.get('doi') and ('title' not in metadata or not metadata['title']):
                    crossref_metadata = fetch_metadata_from_crossref(metadata['doi'])
                    if crossref_metadata:
                        # Format the metadata
                        metadata.update({
                            "title": crossref_metadata.get("title", [""])[0] if isinstance(crossref_metadata.get("title"), list) else crossref_metadata.get("title", ""),
                            "authors": crossref_metadata.get("author", []),
                            "publication_date": crossref_metadata.get("published", {}).get("date-parts", [[""]])[0][0],
                            "journal": crossref_metadata.get("container-title", [""])[0] if isinstance(crossref_metadata.get("container-title"), list) else "",
                            "publisher": crossref_metadata.get("publisher", ""),
                            "volume": crossref_metadata.get("volume", ""),
                            "issue": crossref_metadata.get("issue", ""),
                            "pages": crossref_metadata.get("page", ""),
                            "type": crossref_metadata.get("type", ""),
                        })
                
                # Process chunks if requested
                if metadata.get('processChunks', True):
                    chunk_size = metadata.get('chunkSize', 1000)
                    overlap = metadata.get('chunkOverlap', 200)
                    
                    # Chunk the text
                    chunks = chunk_text(extracted_text, chunk_size, overlap)
                    
                    # Determine which collection to use based on document type
                    doc_type = metadata.get('type', '').lower()
                    collection = books_collection if 'book' in doc_type else papers_collection
                    
                    # Prepare document IDs for the chunks
                    chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
                    
                    # Add document metadata to each chunk's metadata
                    chunk_metadatas = []
                    for i in range(len(chunks)):
                        # Calculate approximate page number
                        chunk_start_pos = i * (chunk_size - overlap) if i > 0 else 0
                        approx_page = max(1, chunk_start_pos // 3000)  # Rough estimate: ~3000 chars per page
                        
                        chunk_metadata = {
                            **metadata,
                            "chunk_index": i,
                            "chunk_total": len(chunks),
                            "approx_page": approx_page
                        }
                        chunk_metadatas.append(chunk_metadata)
                    
                    # Add to vector database
                    collection.add(
                        documents=chunks,
                        metadatas=chunk_metadatas,
                        ids=chunk_ids
                    )
                    
                    # Update metadata with chunk info
                    metadata['processed'] = True
                    metadata['num_chunks'] = len(chunks)
                    metadata['chunk_size'] = chunk_size
                    metadata['overlap'] = overlap
                
                # Add upload metadata
                metadata['document_id'] = document_id
                metadata['filename'] = filename
                metadata['upload_date'] = datetime.now().isoformat()
                metadata['file_path'] = str(filepath)
                
                # Save metadata to a JSON file alongside the PDF
                metadata_path = filepath.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return jsonify(metadata)
                
            except Exception as e:
                # Clean up if there's an error
                if filepath.exists():
                    filepath.unlink()
                print(f"Error processing document: {e}")
                return jsonify({"error": str(e)}), 500
        
        # If no file but only metadata update
        else:
            try:
                # Find the document file
                files = list(UPLOAD_FOLDER.glob(f"{document_id}_*"))
                if not files:
                    return jsonify({"error": "Document not found"}), 404
                    
                filepath = [f for f in files if f.suffix.lower() == '.pdf'][0]
                
                # Update metadata
                metadata['document_id'] = document_id
                metadata['update_date'] = datetime.now().isoformat()
                
                # Save metadata to a JSON file
                metadata_path = filepath.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return jsonify(metadata)
                
            except Exception as e:
                print(f"Error updating document metadata: {e}")
                return jsonify({"error": str(e)}), 500

    @app.route('/api/documents/<document_id>', methods=['DELETE'])
    def delete_document(document_id):
        """Delete a document and its metadata."""
        try:
            # Find all files for this document
            files = list(UPLOAD_FOLDER.glob(f"{document_id}_*"))
            if not files:
                return jsonify({"error": "Document not found"}), 404
            
            # Delete PDF and metadata files
            for file in files:
                file.unlink()
            
            # Remove from vector database
            doc_type = ""
            for collection in [papers_collection, books_collection]:
                try:
                    # Get chunk IDs
                    results = collection.get(
                        where={"document_id": document_id}
                    )
                    if results and results['ids']:
                        # Delete chunks
                        collection.delete(
                            ids=results['ids']
                        )
                except Exception as e:
                    print(f"Error removing document from vector database: {e}")
            
            return jsonify({"success": True})
            
        except Exception as e:
            print(f"Error deleting document: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/query', methods=['POST'])
    def query_documents():
        """Query the vector database for relevant documents."""
        data = request.json
        
        if not data or 'query' not in data:
            return jsonify({"error": "Missing query"}), 400
            
        query_text = data['query']
        citation_style = data.get('citation_style', 'apa')
        n_results = data.get('n_results', 5)
        document_ids = data.get('document_ids', [])
        
        try:
            # Build where clause for filtering by document_ids
            where_clause = {}
            if document_ids and len(document_ids) > 0:
                where_clause = {"document_id": {"$in": document_ids}}
            
            # Query both collections
            papers_results = papers_collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            books_results = books_collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            # Combine and sort results by distance
            combined_results = []
            
            if papers_results['documents'] and papers_results['documents'][0]:
                for i in range(len(papers_results['documents'][0])):
                    combined_results.append({
                        "document": papers_results['documents'][0][i],
                        "metadata": papers_results['metadatas'][0][i],
                        "distance": papers_results['distances'][0][i] if 'distances' in papers_results else 0,
                        "id": papers_results['ids'][0][i]
                    })
                    
            if books_results['documents'] and books_results['documents'][0]:
                for i in range(len(books_results['documents'][0])):
                    combined_results.append({
                        "document": books_results['documents'][0][i],
                        "metadata": books_results['metadatas'][0][i],
                        "distance": books_results['distances'][0][i] if 'distances' in books_results else 0,
                        "id": books_results['ids'][0][i]
                    })
            
            # Sort by relevance (ascending distance)
            combined_results.sort(key=lambda x: x['distance'])
            
            # Prepare response with citations
            processed_results = []
            citations = []
            citation_keys = {}  # To track unique citations
            
            for result in combined_results[:n_results]:
                metadata = result['metadata']
                doc_id = metadata.get('document_id')
                
                # Create citation key (e.g., "Smith2019")
                authors = metadata.get('authors', [])
                year = ""
                if 'publication_date' in metadata:
                    match = re.search(r'(\d{4})', metadata['publication_date'])
                    if match:
                        year = match.group(1)
                
                author_name = ""
                if authors and isinstance(authors, list) and len(authors) > 0:
                    if 'family' in authors[0]:
                        author_name = authors[0]['family']
                    elif 'name' in authors[0]:
                        name_parts = authors[0]['name'].split()
                        if name_parts:
                            author_name = name_parts[-1]  # Last name
                
                citation_key = f"{author_name}{year}"
                if not citation_key:
                    citation_key = f"Doc{len(citation_keys) + 1}"
                    
                # Handle duplicate keys
                if citation_key in citation_keys:
                    citation_keys[citation_key] += 1
                    citation_key = f"{citation_key}{chr(96 + citation_keys[citation_key])}"  # Add a, b, c, etc.
                else:
                    citation_keys[citation_key] = 1
                
                # Format citation
                citation = format_citation(metadata, citation_style)
                if citation and citation not in citations:
                    citations.append(citation)
                
                # Add page number if available
                page_info = ""
                if 'approx_page' in metadata:
                    page_info = f", p. {metadata['approx_page']}"
                
                # Add to processed results
                processed_results.append({
                    "text": result['document'],
                    "source": f"({citation_key}{page_info})",
                    "metadata": metadata,
                    "distance": result['distance']
                })
            
            return jsonify({
                "results": processed_results,
                "bibliography": citations,
                "query": query_text
            })
            
        except Exception as e:
            print(f"Error querying documents: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/query/citation-styles', methods=['GET'])
    def get_citation_styles():
        """Get available citation styles."""
        try:
            styles = [
                {"id": "apa", "name": "APA 7th Edition"},
                {"id": "chicago", "name": "Chicago 18th Edition"},
                {"id": "harvard", "name": "Harvard"}
            ]
            
            return jsonify(styles)
            
        except Exception as e:
            print(f"Error retrieving citation styles: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/metadata/doi/<path:doi>', methods=['GET'])
    def get_doi_metadata(doi):
        """Get metadata for a DOI."""
        try:
            crossref_metadata = fetch_metadata_from_crossref(doi)
            if not crossref_metadata:
                return jsonify({"error": "DOI not found"}), 404
                
            # Format metadata
            metadata = {
                "title": crossref_metadata.get("title", [""])[0] if isinstance(crossref_metadata.get("title"), list) else crossref_metadata.get("title", ""),
                "authors": crossref_metadata.get("author", []),
                "publication_date": crossref_metadata.get("published", {}).get("date-parts", [[""]])[0][0],
                "journal": crossref_metadata.get("container-title", [""])[0] if isinstance(crossref_metadata.get("container-title"), list) else "",
                "publisher": crossref_metadata.get("publisher", ""),
                "volume": crossref_metadata.get("volume", ""),
                "issue": crossref_metadata.get("issue", ""),
                "pages": crossref_metadata.get("page", ""),
                "type": crossref_metadata.get("type", ""),
                "doi": doi
            }
            
            return jsonify(metadata)
            
        except Exception as e:
            print(f"Error retrieving DOI metadata: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/metadata/isbn/<isbn>', methods=['GET'])
    def get_isbn_metadata(isbn):
        """Get metadata for an ISBN."""
        try:
            # TODO: Implement ISBN lookup via Google Books or Open Library
            return jsonify({"error": "ISBN lookup not implemented yet"}), 501
            
        except Exception as e:
            print(f"Error retrieving ISBN metadata: {e}")
            return jsonify({"error": str(e)}), 500

    return app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=True)