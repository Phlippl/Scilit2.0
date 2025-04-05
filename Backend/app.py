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

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuration
UPLOAD_FOLDER = Path('./uploads')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB max upload size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directory if it doesn't exist
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Initialize spaCy
try:
    nlp = spacy.load("en_core_web_lg")
    print("Loaded spaCy model: en_core_web_lg")
except OSError:
    print("Downloading spaCy model...")
    spacy.cli.download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

# Create collections for different document types
papers_collection = chroma_client.get_or_create_collection(name="academic_papers")
books_collection = chroma_client.get_or_create_collection(name="books")

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

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle PDF upload and processing."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400
    
    # Save the uploaded file
    filename = secure_filename(file.filename)
    doc_id = str(uuid.uuid4())
    filepath = UPLOAD_FOLDER / f"{doc_id}_{filename}"
    file.save(filepath)
    
    try:
        # Extract text from PDF
        extracted_text = extract_text_from_pdf(filepath)
        
        # Extract identifiers
        doi = extract_doi(extracted_text)
        isbn = extract_isbn(extracted_text)
        
        # Initial metadata
        metadata = {
            "document_id": doc_id,
            "filename": filename,
            "doi": doi,
            "isbn": isbn,
            "upload_date": datetime.now().isoformat(),
            "processed": False
        }
        
        # Fetch metadata from CrossRef if DOI is available
        if doi:
            crossref_metadata = fetch_metadata_from_crossref(doi)
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
        
        return jsonify({
            "success": True,
            "document_id": doc_id,
            "metadata": metadata,
            "doi_found": doi is not None,
            "isbn_found": isbn is not None,
            "text_length": len(extracted_text)
        })
        
    except Exception as e:
        # Clean up if there's an error
        if filepath.exists():
            filepath.unlink()
        return jsonify({"error": str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_document():
    """Process document and store in vector database."""
    data = request.json
    
    if not data or 'document_id' not in data or 'metadata' not in data:
        return jsonify({"error": "Missing required data"}), 400
        
    document_id = data['document_id']
    metadata = data['metadata']
    chunk_size = data.get('chunk_size', 1000)
    overlap = data.get('overlap', 200)
    
    # Find the document file
    files = list(UPLOAD_FOLDER.glob(f"{document_id}_*"))
    if not files:
        return jsonify({"error": "Document not found"}), 404
        
    filepath = files[0]
    
    try:
        # Extract text
        extracted_text = extract_text_from_pdf(filepath)
        
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
        
        # Update metadata to mark as processed
        metadata['processed'] = True
        metadata['num_chunks'] = len(chunks)
        metadata['chunk_size'] = chunk_size
        metadata['overlap'] = overlap
        metadata['processing_date'] = datetime.now().isoformat()
        
        # Save metadata to a JSON file alongside the PDF
        metadata_path = filepath.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return jsonify({
            "success": True,
            "document_id": document_id,
            "chunks_created": len(chunks),
            "metadata": metadata
        })
        
    except Exception as e:
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
    
    try:
        # Query both collections
        papers_results = papers_collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        books_results = books_collection.query(
            query_texts=[query_text],
            n_results=n_results
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
            "total_results": len(combined_results)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        
        return jsonify({
            "documents": sorted(documents, key=lambda x: x.get('upload_date', ''), reverse=True)
        })
        
    except Exception as e:
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
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)