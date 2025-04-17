# Backend/services/document_analysis_service.py
from services.document_processing_service import DocumentProcessorService
from api.documents.document_status import update_document_status

class DocumentAnalysisService(DocumentProcessorService):
    """Service für temporäre Dokumentenanalyse ohne persistente Speicherung"""
    
    def analyze_document(self, document_id, filepath, settings):
        """Analysiert ein Dokument und gibt die Ergebnisse zurück"""
        # Status initialisieren
        update_document_status(
            document_id=document_id,
            status="processing",
            progress=0,
            message="Starting document analysis..."
        )
        
        try:
            # Basis-Verarbeitung durchführen
            result = self.process_document(
                document_id=document_id,
                filepath=filepath,
                settings=settings,
                cleanup_file=True  # Temporäre Datei automatisch löschen
            )
            
            # Limitierung der zurückgegebenen Chunks für die API-Response
            MAX_CHUNKS_IN_RESPONSE = 100
            chunks = result.get('chunks', [])
            if len(chunks) > MAX_CHUNKS_IN_RESPONSE:
                limited_chunks = chunks[:MAX_CHUNKS_IN_RESPONSE]
                result.update({
                    'limitedChunks': True,
                    'totalChunks': len(chunks),
                    'chunks': limited_chunks
                })
            
            # Status aktualisieren
            update_document_status(
                document_id=document_id,
                status="completed",
                progress=100,
                message="Analysis complete",
                result=result
            )
            
            return result
            
        except Exception as e:
            # Status bei Fehler aktualisieren
            update_document_status(
                document_id=document_id,
                status="error",
                progress=0,
                message=f"Error analyzing document: {str(e)}",
                result={"error": str(e)}
            )
            raise