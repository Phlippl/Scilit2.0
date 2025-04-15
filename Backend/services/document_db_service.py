import os
import json
import logging
from datetime import datetime
import uuid
import mysql.connector
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class DocumentDBService:
    """Service for document management with MySQL database"""
    
    def __init__(self, db_config=None):
        # Load environment variables
        load_dotenv()

        # Set up database configuration
        if db_config:
            self.db_config = db_config
        else:
            self.db_config = {
                'host': os.environ.get('MYSQL_HOST', 'localhost'),
                'user': os.environ.get('MYSQL_USER', 'root'),
                'password': os.environ.get('MYSQL_PASSWORD', ''),
                'database': os.environ.get('MYSQL_DATABASE', 'scilit2'),
                'port': int(os.environ.get('MYSQL_PORT', 3306))
            }
        
        # Create database connection
        self._ensure_connection()
    
    def _ensure_connection(self):
        """Ensure database connection is established or create tables as fallback"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            # Test connection
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            connection.close()
            logger.info("Database connection successful")
        except mysql.connector.Error as err:
            logger.warning(f"Database connection failed: {err}")
            # Fallback to file-based storage
            logger.info("Falling back to file-based storage")
            
            # Create uploads directory
            upload_folder = os.environ.get('UPLOAD_FOLDER', './uploads')
            os.makedirs(upload_folder, exist_ok=True)
    
    def save_document_metadata(self, document_id, user_id, title, file_name, file_path, file_size, metadata=None):
        """Save document metadata to database or file"""
        connection = None
        cursor = None
        try:
            # Try to connect to database
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            user_exists = cursor.fetchone()
            
            if not user_exists:
                logger.warning(f"User with ID {user_id} does not exist. Using as is.")
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Convert metadata to JSON
            metadata_json = json.dumps(metadata) if metadata else '{}'
            
            # Insert or update document
            cursor.execute('''
            INSERT INTO documents 
            (id, user_id, title, file_name, file_path, file_size, upload_date, metadata, processing_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            title = %s,
            file_name = %s,
            file_path = %s,
            file_size = %s,
            metadata = %s,
            processing_status = %s
            ''', (
                document_id, user_id, title, file_name, file_path, file_size, now, metadata_json, 'processing',
                title, file_name, file_path, file_size, metadata_json, 'processing'
            ))
            
            connection.commit()
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Database error: {str(e)}")
            
            # Fallback to file-based storage
            try:
                # Save metadata to JSON file next to document
                metadata_file = f"{file_path}.json"
                
                # Prepare metadata
                metadata_to_save = metadata or {}
                metadata_to_save.update({
                    'id': document_id,
                    'user_id': user_id,
                    'title': title,
                    'file_name': file_name,
                    'file_path': file_path,
                    'file_size': file_size,
                    'upload_date': now if 'now' in locals() else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'processing_status': 'processing'
                })
                
                # Save to file
                with open(metadata_file, 'w') as f:
                    json.dump(metadata_to_save, f, indent=2)
                
                return True
            except Exception as file_err:
                logger.error(f"Fallback storage error: {str(file_err)}")
                return False
        except Exception as e:
            logger.error(f"Error saving document metadata: {str(e)}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def update_document_status(self, document_id, status, progress=None, message=None):
        """Update document processing status"""
        connection = None
        cursor = None
        try:
            # Try database update
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Create status metadata
            status_metadata = json.dumps({
                'status': status,
                'progress': progress,
                'message': message,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Update document status
            cursor.execute('''
            UPDATE documents 
            SET processing_status = %s, 
                metadata = JSON_SET(metadata, '$.processing', %s)
            WHERE id = %s
            ''', (status, status_metadata, document_id))
            
            connection.commit()
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Database error updating status: {str(e)}")
            
            # Fallback: find document metadata file and update it
            try:
                # Get upload folder
                upload_folder = os.environ.get('UPLOAD_FOLDER', './uploads')
                
                # Create status file
                status_file = os.path.join(upload_folder, 'status', f"{document_id}_status.json")
                
                status_data = {
                    'status': status,
                    'progress': progress,
                    'message': message,
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Save status to file
                os.makedirs(os.path.dirname(status_file), exist_ok=True)
                with open(status_file, 'w') as f:
                    json.dump(status_data, f, indent=2)
                
                return True
            except Exception as file_err:
                logger.error(f"Fallback status update error: {str(file_err)}")
                return False
        except Exception as e:
            logger.error(f"Error updating document status: {str(e)}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def get_documents_by_user(self, user_id):
        """Get all documents for a user from database or files"""
        connection = None
        cursor = None
        try:
            # Try database query
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            
            # Get documents for user
            cursor.execute('''
            SELECT id, user_id, title, file_name, file_path, file_size, upload_date, processing_status, metadata
            FROM documents WHERE user_id = %s
            ORDER BY upload_date DESC
            ''', (user_id,))
            
            documents = cursor.fetchall()
            
            # Process documents
            for doc in documents:
                if 'upload_date' in doc:
                    doc['upload_date'] = doc['upload_date'].strftime('%Y-%m-%d %H:%M:%S')
                
                if 'metadata' in doc and doc['metadata']:
                    try:
                        doc['metadata'] = json.loads(doc['metadata'])
                    except json.JSONDecodeError:
                        doc['metadata'] = {}
            
            return documents
            
        except mysql.connector.Error as e:
            logger.error(f"Database error retrieving documents: {str(e)}")
            
            # Fallback: find documents in files
            try:
                # Get upload folder
                upload_folder = os.environ.get('UPLOAD_FOLDER', './uploads')
                user_folder = os.path.join(upload_folder, user_id)
                
                if not os.path.exists(user_folder):
                    return []
                
                # Find all JSON metadata files
                documents = []
                for root, _, files in os.walk(user_folder):
                    for file in files:
                        if file.endswith('.json'):
                            try:
                                with open(os.path.join(root, file), 'r') as f:
                                    doc = json.load(f)
                                    if doc.get('user_id') == user_id:
                                        documents.append(doc)
                            except Exception as file_err:
                                logger.error(f"Error reading document file: {str(file_err)}")
                
                # Sort by upload date
                documents.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
                return documents
            except Exception as file_err:
                logger.error(f"Fallback document retrieval error: {str(file_err)}")
                return []
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def delete_document(self, document_id, user_id):
        """Delete document from database and file system"""
        connection = None
        cursor = None
        try:
            # Get document info
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            
            # Find document
            cursor.execute('''
            SELECT file_path FROM documents
            WHERE id = %s AND user_id = %s
            ''', (document_id, user_id))
            
            document = cursor.fetchone()
            
            if not document:
                # Try fallback lookup in files
                try:
                    # Get upload folder
                    upload_folder = os.environ.get('UPLOAD_FOLDER', './uploads')
                    user_folder = os.path.join(upload_folder, user_id)
                    
                    # Look for document metadata file
                    document = None
                    doc_path = None
                    for root, _, files in os.walk(user_folder):
                        for file in files:
                            if file.startswith(f"{document_id}_") and file.endswith('.json'):
                                try:
                                    with open(os.path.join(root, file), 'r') as f:
                                        doc = json.load(f)
                                        if doc.get('id') == document_id:
                                            document = doc
                                            doc_path = doc.get('file_path')
                                except Exception:
                                    pass
                    
                    if not document:
                        return False, "Document not found"
                    
                    # Delete files
                    files_to_delete = []
                    for root, _, files in os.walk(user_folder):
                        for file in files:
                            if file.startswith(f"{document_id}_"):
                                files_to_delete.append(os.path.join(root, file))
                    
                    # Delete each file
                    for file_path in files_to_delete:
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            logger.error(f"Error deleting file {file_path}: {e}")
                    
                    # Delete status file
                    status_file = os.path.join(upload_folder, 'status', f"{document_id}_status.json")
                    if os.path.exists(status_file):
                        try:
                            os.remove(status_file)
                        except Exception as e:
                            logger.error(f"Error deleting status file {status_file}: {e}")
                    
                    # Delete from vector DB
                    try:
                        from services.vector_db import delete_document as delete_from_vector_db
                        delete_from_vector_db(document_id, user_id)
                    except Exception as e:
                        logger.error(f"Error deleting from vector DB: {e}")
                    
                    return True, None
                except Exception as e:
                    logger.error(f"Fallback document deletion error: {e}")
                    return False, str(e)
            
            # Delete from database
            cursor.execute('''
            DELETE FROM documents
            WHERE id = %s AND user_id = %s
            ''', (document_id, user_id))
            
            connection.commit()
            
            # Delete files
            file_path = document['file_path']
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # Also delete JSON metadata if exists
                metadata_path = f"{file_path}.json"
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
            
            # Delete status file
            upload_folder = os.environ.get('UPLOAD_FOLDER', './uploads')
            status_file = os.path.join(upload_folder, 'status', f"{document_id}_status.json")
            if os.path.exists(status_file):
                os.remove(status_file)
            
            # Delete from vector DB
            try:
                from services.vector_db import delete_document as delete_from_vector_db
                delete_from_vector_db(document_id, user_id)
            except Exception as e:
                logger.error(f"Error deleting from vector DB: {e}")
            
            return True, None
            
        except mysql.connector.Error as e:
            logger.error(f"Database error deleting document: {str(e)}")
            if connection:
                connection.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            if connection:
                connection.rollback()
            return False, f"Error deleting document: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()