import os
import uuid
import shutil
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import logging

# Configure logging
logger = logging.getLogger(__name__)

class DocumentService:
    """Service for handling document operations"""
    
    def __init__(self):
        # In-memory storage for documents (replace with database in production)
        self.documents = {}
        # Add a sample document for testing
        self._create_sample_documents()
    
    def _create_sample_documents(self):
        """Create sample documents for testing"""
        if not self.documents:
            # Sample document 1
            self._add_sample_document(
                user_email='user@example.com',
                title='Understanding Vector Databases in Scientific Research',
                authors='Smith, John; Johnson, Emily; Lee, Robert',
                year='2023',
                journal='Journal of Data Science',
                volume='15',
                issue='4',
                pages='425-442',
                doi='10.1234/scilit.2023.0001'
            )
            
            # Sample document 2
            self._add_sample_document(
                user_email='user@example.com',
                title='The Future of AI in Academic Publishing',
                authors='Williams, Sarah; Brown, David',
                year='2022',
                journal='AI Review',
                volume='8',
                issue='2',
                pages='112-128',
                doi='10.5678/airev.2022.0015'
            )
            
            # Sample document 3
            self._add_sample_document(
                user_email='user@example.com',
                title='Natural Language Processing: Fundamentals and Applications',
                authors='Garcia, Maria',
                year='2021',
                publisher='Academic Press',
                isbn='978-3-16-148410-0',
                type='book'
            )
    
    def _add_sample_document(self, user_email, title, authors, year, **kwargs):
        """Add a sample document"""
        doc_id = str(uuid.uuid4())
        
        document = {
            'id': doc_id,
            'user_email': user_email,
            'title': title,
            'authors': authors,
            'year': year,
            'upload_date': datetime.now().strftime('%Y-%m-%d'),
            'type': kwargs.get('type', 'article'),
            'citation_style': 'apa7',
            'file_path': 'sample/path/document.pdf'  # Fake path
        }
        
        # Add article-specific fields
        if document['type'] == 'article':
            document.update({
                'journal': kwargs.get('journal', ''),
                'volume': kwargs.get('volume', ''),
                'issue': kwargs.get('issue', ''),
                'pages': kwargs.get('pages', ''),
                'doi': kwargs.get('doi', '')
            })
        else:
            # Add book-specific fields
            document.update({
                'publisher': kwargs.get('publisher', ''),
                'isbn': kwargs.get('isbn', '')
            })
        
        # Store document
        self.documents[doc_id] = document
    
    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        ALLOWED_EXTENSIONS = {'pdf'}
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def save_file(self, file, upload_folder):
        """Save an uploaded file to the temporary folder"""
        filename = secure_filename(file.filename)
        temp_filename = f"{str(uuid.uuid4())}_{filename}"
        file_path = os.path.join(upload_folder, temp_filename)
        file.save(file_path)
        return file_path
    
    def extract_text(self, file_path):
        """Extract text from a PDF file using PyPDF2 or fallback to OCR if needed"""
        try:
            # First try to extract text directly using PyPDF2
            import PyPDF2
            text = ""
            try:
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page_num in range(len(pdf_reader.pages)):
                        text += pdf_reader.pages[page_num].extract_text() + "\n"
            except Exception as e:
                logger.error(f"Error in direct text extraction: {str(e)}")
                return ""
            
            # If direct extraction yields little text, use OCR
            if len(text.strip()) < 100:
                logger.info(f"Direct text extraction yielded minimal text, using OCR for {file_path}")
                return self._extract_text_ocr(file_path)
            
            return text
        
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return ""
    
    def _extract_text_ocr(self, file_path):
        """Extract text from PDF using OCR"""
        text = ""
        try:
            # Import OCR libraries
            from pdf2image import convert_from_path
            import pytesseract
            
            # Convert PDF to images
            images = convert_from_path(file_path)
            
            # Perform OCR on each image
            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(image)
                text += f"Page {i+1}:\n{page_text}\n\n"
            
            return text
        except ImportError as e:
            logger.error(f"OCR dependencies not available: {e}")
            return ""
        except Exception as e:
            logger.error(f"Error in OCR text extraction: {e}")
            return ""
    
    def save_document_metadata(self, user_email, metadata):
        """Save document metadata to database"""
        doc_id = str(uuid.uuid4())
        
        # Create document record
        document = {
            'id': doc_id,
            'user_email': user_email,
            'title': metadata.get('title', ''),
            'authors': metadata.get('authors', ''),
            'year': metadata.get('year', ''),
            'upload_date': datetime.now().strftime('%Y-%m-%d'),
            'citation_style': metadata.get('citationStyle', 'apa7'),
            'type': 'book' if metadata.get('isbn') else 'article'
        }
        
        # Add type-specific fields
        if document['type'] == 'article':
            document.update({
                'journal': metadata.get('journal', ''),
                'volume': metadata.get('volume', ''),
                'issue': metadata.get('issue', ''),
                'pages': metadata.get('pages', ''),
                'doi': metadata.get('doi', '')
            })
        else:
            document.update({
                'publisher': metadata.get('publisher', ''),
                'isbn': metadata.get('isbn', '')
            })
        
        # Store document
        self.documents[doc_id] = document
        
        return doc_id
    
    def move_to_permanent_storage(self, file_path, document_id, user_email):
        """Move a file from temporary storage to permanent storage"""
        # Create user directory if it doesn't exist
        user_dir = os.path.join(os.path.dirname(os.path.dirname(file_path)), 'documents', user_email)
        os.makedirs(user_dir, exist_ok=True)
        
        # Get file extension
        _, ext = os.path.splitext(file_path)
        
        # Generate new filename
        new_filename = f"{document_id}{ext}"
        new_path = os.path.join(user_dir, new_filename)
        
        # Move file
        shutil.move(file_path, new_path)
        
        # Update document record with file path
        if document_id in self.documents:
            self.documents[document_id]['file_path'] = new_path
        
        return new_path
    
    def get_documents_by_user(self, user_email):
        """Get all documents for a user"""
        user_documents = []
        
        for doc_id, document in self.documents.items():
            if document['user_email'] == user_email:
                # Create a copy without the file path
                doc_copy = document.copy()
                doc_copy.pop('file_path', None)
                user_documents.append(doc_copy)
        
        return user_documents
    
    def get_document_by_id(self, document_id, user_email):
        """Get a document by ID and verify ownership"""
        document = self.documents.get(document_id)
        
        if not document or document['user_email'] != user_email:
            return None
        
        # Create a copy without the file path
        doc_copy = document.copy()
        doc_copy.pop('file_path', None)
        
        return doc_copy
    
    def delete_document(self, document_id, user_email):
        """Delete a document and its file"""
        document = self.documents.get(document_id)
        
        if not document or document['user_email'] != user_email:
            return False
        
        # Delete file if it exists
        if 'file_path' in document and os.path.exists(document['file_path']):
            try:
                os.remove(document['file_path'])
            except Exception as e:
                logger.error(f"Error deleting file {document['file_path']}: {str(e)}")
        
        # Delete document from storage
        self.documents.pop(document_id, None)
        
        return True