# Backend/services/pdf/ocr.py
"""
OCR-Komponente für die PDF-Verarbeitung
"""
import io
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Prüfe ob OCR-Abhängigkeiten verfügbar sind
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    logger.warning("pytesseract or PIL not available, OCR functionality will be limited")
    OCR_AVAILABLE = False

class OCRProcessor:
    """
    Komponente für OCR-Verarbeitung
    """
    
    def __init__(self):
        """
        Initialisiert den OCR-Processor
        """
        self.available = OCR_AVAILABLE
    
    def process_image(self, image_data: bytes, lang: str = 'eng+deu') -> str:
        """
        Führt OCR auf Bilddaten durch
        
        Args:
            image_data: Bilddaten als Bytes
            lang: Sprachcode(s) für OCR
            
        Returns:
            str: Extrahierter Text
        """
        if not self.available:
            logger.warning("OCR requested but not available (missing dependencies)")
            return ""
        
        try:
            # Konvertiere zu PIL Image
            img = Image.open(io.BytesIO(image_data))
            
            # Führe OCR durch
            text = pytesseract.image_to_string(img, lang=lang)
            
            logger.debug(f"OCR complete, extracted {len(text)} chars")
            return text
        except Exception as e:
            logger.error(f"Error in OCR processing: {e}")
            return ""
    
    def can_perform_ocr(self) -> bool:
        """
        Prüft, ob OCR verfügbar ist
        
        Returns:
            bool: True wenn OCR verfügbar ist
        """
        return self.available
    
    def get_ocr_info(self) -> dict:
        """
        Gibt Informationen über die OCR-Verfügbarkeit zurück
        
        Returns:
            dict: Informationen über OCR-Verfügbarkeit und -Konfiguration
        """
        info = {
            "available": self.available,
            "library": "pytesseract" if self.available else None
        }
        
        if self.available:
            try:
                # Versuche, Tesseract-Version zu bekommen
                version = pytesseract.get_tesseract_version()
                info["version"] = version
            except Exception:
                info["version"] = "unknown"
        
        return info