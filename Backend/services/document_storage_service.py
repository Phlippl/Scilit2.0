# Backend/services/document_storage_service.py
from services.document_processing_service import DocumentProcessorService
from services.vector_db import store_document_chunks
from api.documents.document_status import update_document_status
from utils.metadata_utils import format_metadata_for_storage

class DocumentStorageService(DocumentProcessorService):
    """Service für vollständige Dokumentenverarbeitung mit persistenter Speicherung"""
    
    def process_and_store_document(self, document_id, filepath, metadata, settings):
        """Verarbeitet ein Dokument und speichert es dauerhaft"""
        # Status initialisieren
        update_document_status(
            document_id=document_id,
            status="processing",
            progress=0,
            message="Starting document processing..."
        )
        
        try:
            # Basis-Verarbeitung durchführen
            result = self.process_document(
                document_id=document_id,
                filepath=filepath,
                settings=settings
            )
            
            # Metadaten-Aktualisierung
            if result['metadata'].get('doi') and not metadata.get('doi'):
                metadata['doi'] = result['metadata']['doi']
            
            if result['metadata'].get('isbn') and not metadata.get('isbn'):
                metadata['isbn'] = result['metadata']['isbn']
            
            # Status aktualisieren
            update_document_status(
                document_id=document_id,
                status="processing",
                progress=85,
                message="Storing chunks in vector database..."
            )
            
            # In Vektordatenbank speichern
            chunks_stored = False
            if result['chunks'] and len(result['chunks']) > 0:
                # Angemessene Chunk-Begrenzung
                max_chunks = min(len(result['chunks']), 500)
                limited_chunks = result['chunks'][:max_chunks]
                
                # Metadaten formatieren
                formatted_metadata = format_metadata_for_storage(metadata)
                
                # Speichern
                store_result = store_document_chunks(
                    document_id=document_id,
                    chunks=limited_chunks,
                    metadata=formatted_metadata
                )
                chunks_stored = store_result
                
                # Metadata aktualisieren
                metadata['processed'] = store_result
                metadata['num_chunks'] = len(limited_chunks)
                metadata['chunk_size'] = settings.get('chunkSize', 1000)
                metadata['chunk_overlap'] = settings.get('chunkOverlap', 200)
            
            # Abschluss der Verarbeitung in Metadaten
            metadata['processingComplete'] = chunks_stored
            metadata['processedDate'] = result.get('processedDate', 
                                                 metadata.get('processedDate'))
            
            # Status aktualisieren
            update_document_status(
                document_id=document_id,
                status="completed" if chunks_stored else "completed_with_warnings",
                progress=100,
                message="Document processing completed" if chunks_stored else 
                         "Document processed but chunks could not be stored"
            )
            
            return result, metadata
            
        except Exception as e:
            # Status und Metadata bei Fehler aktualisieren
            update_document_status(
                document_id=document_id,
                status="error",
                progress=0,
                message=f"Error processing document: {str(e)}"
            )
            
            # Fehler in Metadaten vermerken
            metadata['processingComplete'] = False
            metadata['processingError'] = str(e)
            
            raise