import os
import json
import logging
from datetime import datetime
import mysql.connector
import uuid
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class DocumentDBService:
    """Service für Dokumentenverwaltung mit MySQL"""
    
    def __init__(self, db_config=None):
       
        load_dotenv()

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
    
    def save_document_metadata(self, document_id, user_id, title, file_name, file_path, file_size, metadata=None):
        """Dokumentmetadaten in MySQL-Datenbank speichern"""
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Metadaten zu JSON konvertieren
            metadata_json = json.dumps(metadata) if metadata else '{}'
            
            # Dokument einfügen oder aktualisieren
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
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Dokumentmetadaten: {str(e)}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def update_document_status(self, document_id, status, progress=None, message=None):
        """Status eines Dokuments aktualisieren"""
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Status-Metadaten in JSON speichern
            status_metadata = json.dumps({
                'status': status,
                'progress': progress,
                'message': message,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            cursor.execute('''
            UPDATE documents 
            SET processing_status = %s, 
                metadata = JSON_SET(metadata, '$.processing', %s)
            WHERE id = %s
            ''', (status, status_metadata, document_id))
            
            connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Dokumentstatus: {str(e)}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def get_documents_by_user(self, user_id):
        """Alle Dokumente eines Benutzers abrufen"""
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute('''
            SELECT id, user_id, title, file_name, file_path, file_size, upload_date, processing_status, metadata
            FROM documents WHERE user_id = %s
            ORDER BY upload_date DESC
            ''', (user_id,))
            
            documents = cursor.fetchall()
            
            # Dokumente verarbeiten
            for doc in documents:
                if 'upload_date' in doc:
                    doc['upload_date'] = doc['upload_date'].strftime('%Y-%m-%d %H:%M:%S')
                
                if 'metadata' in doc and doc['metadata']:
                    try:
                        doc['metadata'] = json.loads(doc['metadata'])
                    except:
                        doc['metadata'] = {}
            
            return documents
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Dokumente: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def delete_document(self, document_id, user_id):
        """Dokument aus MySQL-Datenbank und Dateisystem löschen"""
        connection = None
        cursor = None
        try:
            # Dokumentinfo abrufen
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute('''
            SELECT file_path FROM documents
            WHERE id = %s AND user_id = %s
            ''', (document_id, user_id))
            
            document = cursor.fetchone()
            
            if not document:
                return False, "Dokument nicht gefunden"
            
            # Aus Datenbank löschen
            cursor.execute('''
            DELETE FROM documents
            WHERE id = %s AND user_id = %s
            ''', (document_id, user_id))
            
            connection.commit()
            
            # Datei löschen, falls vorhanden
            file_path = document['file_path']
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # Auch JSON-Metadaten löschen, falls vorhanden
                metadata_path = f"{file_path}.json"
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
            
            # Aus Vektordatenbank löschen
            from services.vector_db import delete_document as delete_from_vector_db
            delete_from_vector_db(document_id, user_id)
            
            return True, None
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Dokuments: {str(e)}")
            if connection:
                connection.rollback()
            return False, f"Fehler beim Löschen des Dokuments: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()