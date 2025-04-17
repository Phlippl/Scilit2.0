# Backend/services/pdf/__init__.py
"""
Modulares PDF-Verarbeitungspaket
"""
from .processor import PDFProcessor, ProcessingSettings
from .extractors import TextExtractor, IdentifierExtractor
from .chunking import TextChunker
from .ocr import OCRProcessor

# Singleton-Instanz für einfacheren Zugriff
_processor_instance = None

def get_pdf_processor():
    """Gibt die aktuelle PDFProcessor-Instanz zurück"""
    global _processor_instance
    
    if _processor_instance is None:
        _processor_instance = PDFProcessor()
    
    return _processor_instance