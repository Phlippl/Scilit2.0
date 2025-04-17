# Backend/services/document_service_legacy.py
"""
Legacy document service - delegating to newer service implementations.
This file provides backward compatibility for code still using the old API.
"""
import os
import uuid
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional

# Import the new service implementations
from services.document_processing_service import DocumentProcessorService
from services.document_storage_service import DocumentStorageService
from services.document_db_service import DocumentDBService
from services.document_analysis_service import DocumentAnalysisService

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for handling document operations (Legacy API)"""
    
    def __init__(self):
        self.documents = {}
        self.processor = DocumentProcessorService()
        self.storage = DocumentStorageService()
        self.db_service = DocumentDBService()
        self.analysis = DocumentAnalysisService()
        
        # In-memory only for backward compatibility
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
        """Check if file extension is allowed - delegating to utils.helpers"""
        from utils.helpers import allowed_file
        return allowed_file(filename)
    
    def save_file(self, file, upload_folder):
        """Save an uploaded file to the temporary folder"""
        from werkzeug.utils import secure_filename
        
        filename = secure_filename(file.filename)
        temp_filename = f"{str(uuid.uuid4())}_{filename}"
        file_path = os.path.join(upload_folder, temp_filename)
        file.save(file_path)
        return file_path
    
    def extract_text(self, file_path):
        """Extract text from a PDF file - delegating to PDF processor"""
        logger.info(f"Legacy extract_text call for {file_path}, delegating to PDF processor")
        try:
            # Use the new PDF processor
            from services.pdf import get_pdf_processor
            pdf_processor = get_pdf_processor()
            
            # Extract with limited pages
            result = pdf_processor.process_file(
                file_path, 
                settings={
                    'maxPages': 50,  # Limit to 50 pages for quick extraction
                    'performOCR': False,
                    'chunkSize': 1000,
                    'chunkOverlap': 200
                }
            )
            
            return result.get('text', '')
        except Exception as e:
            logger.error(f"Error in legacy extract_text: {e}")
            return ""
    
    def save_document_metadata(self, user_email, metadata):
        """Save document metadata - delegating to document DB service"""
        doc_id = str(uuid.uuid4())
        
        # Map user_email to user_id (simplified for backward compatibility)
        from utils.auth_middleware import get_user_id
        user_id = get_user_id() or 'default_user'
        
        # Use document DB service to save
        self.db_service.save_document_metadata(
            document_id=doc_id,
            user_id=user_id,
            title=metadata.get('title', ''),
            file_name=metadata.get('filename', f"document_{doc_id}.pdf"),
            file_path=metadata.get('filePath', f"uploads/{user_id}/document_{doc_id}.pdf"),
            file_size=metadata.get('fileSize', 0),
            metadata=metadata
        )
        
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
        import shutil
        shutil.move(file_path, new_path)
        
        # Update document record with file path
        if document_id in self.documents:
            self.documents[document_id]['file_path'] = new_path
        
        return new_path
    
    def get_documents_by_user(self, user_email):
        """Get all documents for a user - delegating to DB service"""
        try:
            # Map user_email to user_id (simplified for backward compatibility)
            from utils.auth_middleware import get_user_id
            user_id = get_user_id() or 'default_user'
            
            # Use document DB service to get documents
            documents = self.db_service.get_documents_by_user(user_id)
            
            # If no documents found from DB service, use in-memory sample documents
            if not documents:
                user_documents = []
                for doc_id, document in self.documents.items():
                    if document['user_email'] == user_email:
                        # Create a copy without the file path
                        doc_copy = document.copy()
                        doc_copy.pop('file_path', None)
                        user_documents.append(doc_copy)
                return user_documents
                
            return documents
        except Exception as e:
            logger.error(f"Error in legacy get_documents_by_user: {e}")
            return []
    
    def get_document_by_id(self, document_id, user_email):
        """Get a document by ID and verify ownership"""
        try:
            # Map user_email to user_id (simplified for backward compatibility)
            from utils.auth_middleware import get_user_id
            user_id = get_user_id() or 'default_user'
            
            # Try to get from document DB service first
            documents = self.db_service.get_documents_by_user(user_id)
            
            for doc in documents:
                if doc.get('id') == document_id:
                    # Create a copy without the file path
                    doc_copy = doc.copy()
                    doc_copy.pop('file_path', None)
                    return doc_copy
            
            # If not found in DB, check in-memory store
            document = self.documents.get(document_id)
            if not document or document['user_email'] != user_email:
                return None
            
            # Create a copy without the file path
            doc_copy = document.copy()
            doc_copy.pop('file_path', None)
            
            return doc_copy
        except Exception as e:
            logger.error(f"Error in legacy get_document_by_id: {e}")
            return None
    
    def delete_document(self, document_id, user_email):
        """Delete a document and its file"""
        try:
            # Map user_email to user_id (simplified for backward compatibility)
            from utils.auth_middleware import get_user_id
            user_id = get_user_id() or 'default_user'
            
            # Use document DB service to delete
            success, error = self.db_service.delete_document(document_id, user_id)
            
            if success:
                # Also remove from in-memory store if exists
                self.documents.pop(document_id, None)
                return True
                
            # If DB delete failed, try direct file delete
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
        except Exception as e:
            logger.error(f"Error in legacy delete_document: {e}")
            return False