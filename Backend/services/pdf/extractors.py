# Backend/services/pdf/extractors.py
"""
Extraktionskomponenten für die PDF-Verarbeitung
"""
import os
import logging
import gc
import time
import re
import io
from typing import Dict, Any, List, Optional, Callable, Union
import tempfile

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF not found. Please install: pip install PyMuPDF")

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from utils.identifier_utils import extract_identifiers as utils_extract_identifiers

logger = logging.getLogger(__name__)

class TextExtractor:
    """
    Komponente zur Textextraktion aus PDFs
    """
    
    def __init__(self, cache_size: int = 50):
        """
        Initialisiert den Text-Extraktor
        
        Args:
            cache_size: Maximale Größe des Caches
        """
        self._text_cache = {}
        self.cache_size = cache_size
        
        # Max PDF size and other limits
        self.MAX_FILE_SIZE_MB = 50
        self.WARN_FILE_SIZE_MB = 20
        self.MAX_TEXT_LENGTH = 500000  # 500K characters max for chunking
    
    def validate_pdf(self, filepath: str) -> tuple:
        """
        Validiert ein PDF-Dokument
        
        Args:
            filepath: Pfad zur PDF-Datei
            
        Returns:
            tuple: (is_valid, validation_result)
        """
        try:
            # Prüfe, ob Datei existiert
            if not os.path.exists(filepath):
                logger.error(f"PDF file not found: {filepath}")
                return False, "PDF file not found"
                
            # Prüfe Header-Bytes
            with open(filepath, 'rb') as f:
                header = f.read(5)
                if header != b'%PDF-':
                    logger.error(f"Invalid PDF header: {header}")
                    return False, "Invalid PDF file format (incorrect header)"
            
            # Versuche mit PyMuPDF zu öffnen
            doc = fitz.open(filepath)
            page_count = len(doc)
            logger.info(f"Successfully opened PDF with {page_count} pages")
            doc.close()
            return True, page_count
                
        except Exception as e:
            logger.error(f"PDF validation error: {str(e)}")
            return False, str(e)
    
    def extract_text(self, pdf_file: Union[str, bytes], 
                    max_pages: int = 0, 
                    perform_ocr: bool = False, 
                    progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Extrahiert Text aus einer PDF-Datei mit verbessertem Seiten-Tracking
        
        Args:
            pdf_file: PDF-Dateipfad oder Bytes
            max_pages: Maximale Anzahl zu verarbeitender Seiten (0 = alle)
            perform_ocr: OCR für Seiten mit wenig Text durchführen
            progress_callback: Optionale Fortschrittsrückmeldungsfunktion
        
        Returns:
            dict: Extraktionsergebnis mit Text und Seiteninformationen
        """
        # Prüfe Cache
        file_hash = None
        if isinstance(pdf_file, str) and os.path.exists(pdf_file):
            file_hash = f"{os.path.getsize(pdf_file)}_{os.path.getmtime(pdf_file)}"
            if file_hash in self._text_cache:
                logger.info(f"Using cached text for {pdf_file}")
                return self._text_cache[file_hash]
        
        try:
            logger.info(f"Extracting text from PDF: {pdf_file if isinstance(pdf_file, str) else 'bytes data'}")
            
            # Erstelle temporäre Datei für Bytes-Input
            temp_file = None
            if isinstance(pdf_file, bytes):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_file.write(pdf_file)
                temp_file.close()
                pdf_path = temp_file.name
            else:
                pdf_path = pdf_file
            
            # Öffne PDF
            doc = fitz.open(pdf_path)
            logger.debug(f"Opened PDF with {len(doc)} pages")
            
            # Bereite Ergebnisobjekt vor
            result = {
                'text': '',
                'pages': [],
                'totalPages': len(doc),
                'processedPages': min(len(doc), max_pages) if max_pages > 0 else len(doc)
            }
            
            # Verarbeite Seiten in Batches für besseres Speichermanagement
            pages_to_process = result['processedPages']
            ocr_candidates = []
            BATCH_SIZE = 10  # Verarbeite 10 Seiten auf einmal
            
            for batch_start in range(0, pages_to_process, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, pages_to_process)
                logger.debug(f"Processing batch: pages {batch_start+1}-{batch_end} of {pages_to_process}")
                
                self._process_page_batch(
                    doc=doc,
                    batch_start=batch_start,
                    batch_end=batch_end,
                    result=result,
                    perform_ocr=perform_ocr,
                    ocr_candidates=ocr_candidates,
                    progress_callback=progress_callback
                )
                
                # Erzwinge Garbage Collection nach jedem Batch
                gc.collect()
            
            # Führe OCR für Seiten mit wenig Text durch
            if perform_ocr and ocr_candidates and OCR_AVAILABLE:
                self._perform_ocr_for_candidates(
                    doc=doc,
                    ocr_candidates=ocr_candidates,
                    result=result,
                    progress_callback=progress_callback
                )
            
            # Bereinige
            doc.close()
            if temp_file and os.path.exists(pdf_path):
                os.unlink(pdf_path)
            
            # Cache das Ergebnis wenn wir einen Datei-Hash haben
            if file_hash:
                # Begrenze Cache-Größe
                if len(self._text_cache) >= self.cache_size:
                    # Entferne ältesten Eintrag
                    oldest_key = next(iter(self._text_cache))
                    self._text_cache.pop(oldest_key)
                    
                self._text_cache[file_hash] = result
            
            # Finaler Fortschrittsbericht
            if progress_callback:
                progress_callback("Text extraction complete", 100)
            
            logger.info(f"Text extraction complete. Extracted {len(result['text'])} chars from {len(result['pages'])} pages")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}", exc_info=True)
            
            # Bereinige bei Fehler
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
            raise
    
    def _process_page_batch(self, doc, batch_start, batch_end, result, 
                          perform_ocr, ocr_candidates, progress_callback=None):
        """
        Verarbeitet einen Batch von PDF-Seiten
        
        Args:
            doc: Geöffnetes PyMuPDF-Dokument
            batch_start: Startindex des Batches
            batch_end: Endindex des Batches
            result: Ergebnisobjekt zum Aktualisieren
            perform_ocr: OCR aktivieren
            ocr_candidates: Liste für OCR-Kandidaten
            progress_callback: Fortschrittsrückmeldungsfunktion
        """
        # Verarbeite jede Seite im Batch
        for i in range(batch_start, batch_end):
            page = doc[i]
            
            # Melde Fortschritt
            if progress_callback:
                progress_callback(f"Processing page {i+1}/{result['processedPages']}", 
                                int(i/result['processedPages'] * 100))
            
            # Seiten-Metadaten
            page_info = {
                'pageNumber': i + 1,
                'width': page.rect.width,
                'height': page.rect.height,
                'text': '',
                'startPosition': len(result['text']), # Position im Gesamttext
            }
            
            # Extrahiere Text
            page_text = page.get_text()
            logger.debug(f"Extracted {len(page_text)} characters from page {i+1}")
            
            # Teile große Textblöcke auf, um Speicherprobleme zu vermeiden
            if len(page_text) > 10000:  # 10K Zeichen
                # Verwende natürliche Breaks um Text zu teilen
                split_texts = re.split(r'\n\s*\n', page_text)
                page_text = '\n\n'.join(split_texts)
                logger.debug(f"Split large text block into {len(split_texts)} paragraphs")
                
            page_info['text'] = page_text
            page_info['length'] = len(page_text)
            
            # Füge zum Gesamttext hinzu
            result['text'] += page_text + ' '
            
            # Aktualisiere Endposition
            page_info['endPosition'] = len(result['text']) - 1
            
            # Füge zu OCR-Kandidaten hinzu wenn wenig Text
            if perform_ocr and len(page_text.strip()) < 100:
                logger.debug(f"Adding page {i+1} to OCR candidates (low text content)")
                ocr_candidates.append(i)
            
            result['pages'].append(page_info)
    
    def _perform_ocr_for_candidates(self, doc, ocr_candidates, result, progress_callback=None):
        """
        Führt OCR für Kandidatenseiten durch
        
        Args:
            doc: Geöffnetes PyMuPDF-Dokument
            ocr_candidates: Liste der Seitenindizes für OCR
            result: Ergebnisobjekt zum Aktualisieren
            progress_callback: Fortschrittsrückmeldungsfunktion
        """
        if not OCR_AVAILABLE:
            logger.warning("OCR requested but pytesseract/PIL not available")
            return
        
        logger.info(f"Performing OCR on {len(ocr_candidates)} pages with little text")
        if progress_callback:
            progress_callback(f"Performing OCR on {len(ocr_candidates)} pages", 50)
        
        # Verarbeite OCR in kleineren Batches um Speichernutzung zu begrenzen
        MAX_OCR_PAGES = 5  # Maximale OCR-Seiten in einem Batch
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            for i in range(0, len(ocr_candidates), MAX_OCR_PAGES):
                batch = ocr_candidates[i:i+MAX_OCR_PAGES]
                logger.debug(f"Processing OCR batch: {len(batch)} pages")
                
                # Verarbeite OCR für diesen Batch
                futures = []
                for page_num in batch:
                    future = executor.submit(self._perform_ocr_on_page, doc, page_num, 300)
                    futures.append(future)
                
                # Sammle OCR-Ergebnisse
                for j, future in enumerate(futures):
                    try:
                        page_num, ocr_text = future.result()
                        logger.debug(f"Got OCR result for page {page_num}: {len(ocr_text)} chars")
                        
                        # Konvertiere zu 1-basierten Seitennummern für Index
                        idx = page_num - 1
                        if idx < len(result['pages']):
                            # Aktualisiere Text
                            orig_text = result['pages'][idx]['text']
                            if not orig_text.strip():
                                result['pages'][idx]['text'] = ocr_text
                                # Aktualisiere Gesamttext indem der leere Text ersetzt wird
                                result['text'] = result['text'].replace(orig_text, ocr_text)
                                logger.debug(f"Replaced empty text with OCR text for page {page_num}")
                            else:
                                # Füge OCR-Text an, wenn bereits Text existiert
                                result['pages'][idx]['text'] += ' ' + ocr_text
                                result['text'] += ' ' + ocr_text
                                logger.debug(f"Appended OCR text to existing text for page {page_num}")
                        
                        # Melde Fortschritt
                        if progress_callback:
                            progress_callback(f"OCR processing: {i+j+1}/{len(ocr_candidates)}", 
                                            50 + int((i+j+1)/len(ocr_candidates) * 45))
                    except Exception as e:
                        logger.error(f"Error in OCR process: {e}")
                
                # Erzwinge Garbage Collection nach jedem OCR-Batch
                gc.collect()
    
    @staticmethod
    def _perform_ocr_on_page(doc, page_idx, dpi=300):
        """
        Führt OCR auf einer einzelnen Seite durch
        
        Args:
            doc: Geöffnetes PyMuPDF-Dokument
            page_idx: Seitenindex (0-basiert)
            dpi: DPI für Rendering
        
        Returns:
            tuple: (page_number, ocr_text)
        """
        if not OCR_AVAILABLE:
            logger.warning("OCR requested but pytesseract/PIL not available")
            return page_idx + 1, ""
        
        try:
            if page_idx < 0 or page_idx >= len(doc):
                logger.warning(f"Invalid page index for OCR: {page_idx}")
                return page_idx + 1, ""
            
            # Rendere Seite als Bild
            page = doc[page_idx]
            logger.debug(f"Rendering page {page_idx+1} for OCR at {dpi} DPI")
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
            
            # Konvertiere zu Bild für OCR
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Führe OCR durch
            logger.debug(f"Performing OCR on page {page_idx+1}")
            ocr_text = pytesseract.image_to_string(img)
            logger.debug(f"OCR complete for page {page_idx+1}, extracted {len(ocr_text)} chars")
            
            # Gib Seitennummer (1-basiert) mit Text zurück
            return page_idx + 1, ocr_text
        except Exception as e:
            logger.error(f"Error performing OCR on page {page_idx + 1}: {e}")
            return page_idx + 1, ""
    
    def cleanup_cache(self):
        """Bereinigt den internen Cache"""
        self._text_cache.clear()


class IdentifierExtractor:
    """
    Component to extract identifiers (DOI, ISBN) from PDFs.
    Delegates actual extraction to centralized utils/identifier_utils.py.
    """
    
    def __init__(self, cache_size: int = 50):
        """
        Initialize the identifier extractor
        
        Args:
            cache_size: Maximum size of cache
        """
        self._identifier_cache = {}
        self.cache_size = cache_size
    
    def extract_identifiers(self, text: str, cache_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract DOI and ISBN from text with caching
        
        Args:
            text: Text to search
            cache_key: Optional key for caching
                
        Returns:
            dict: Found identifiers
        """
        # Check cache first
        if cache_key and cache_key in self._identifier_cache:
            logger.debug(f"Using cached identifiers for key: {cache_key}")
            return self._identifier_cache[cache_key]
        
        logger.info("Extracting identifiers from text")
        
        # Use centralized function from identifier_utils
        result = utils_extract_identifiers(text)
        
        # Cache result if key provided
        if cache_key:
            # Limit cache size
            if len(self._identifier_cache) >= self.cache_size:
                # Remove oldest entry
                oldest_key = next(iter(self._identifier_cache))
                self._identifier_cache.pop(oldest_key)
                    
            self._identifier_cache[cache_key] = result
                
        return result
    
    def extract_identifiers_from_pdf(self, filepath: str, max_pages: int = 10) -> Dict[str, Any]:
        """
        Extract only DOI and ISBN from the first pages of a PDF
        
        Args:
            filepath: Path to PDF file
            max_pages: Maximum number of pages to process
            
        Returns:
            dict: Dictionary with found identifiers
        """
        doc = None
        logger.info(f"Extracting identifiers only from: {filepath}, max_pages={max_pages}")
        try:
            # Open PDF
            doc = fitz.open(filepath)
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            logger.info(f"Opened PDF with {len(doc)} pages, size: {file_size_mb:.2f} MB")
            
            # Limit page count
            pages_to_process = min(max_pages, len(doc))
            logger.debug(f"Will process {pages_to_process} pages for identifier extraction")
            
            # Extract text from first pages
            text = ""
            for i in range(pages_to_process):
                page = doc[i]
                page_text = page.get_text()
                logger.debug(f"Extracted {len(page_text)} chars from page {i+1}")
                text += page_text + "\n"
            
            # Extract identifiers using centralized function
            identifiers = utils_extract_identifiers(text)
            doi = identifiers['doi']
            isbn = identifiers['isbn']
            
            # If no DOI/ISBN found and we didn't process all pages, try front and back matter
            if (not doi and not isbn) and pages_to_process < len(doc):
                logger.info("No identifiers found in first pages, checking front and back matter")
                # Try first page and last few pages (often contain publication info)
                back_pages_text = ""
                back_pages_start = max(0, len(doc) - 3)  # Last 3 pages
                for i in range(back_pages_start, len(doc)):
                    if i >= pages_to_process:  # Skip pages we already processed
                        page = doc[i]
                        back_pages_text += page.get_text() + "\n"
                        logger.debug(f"Extracted {len(page.get_text())} chars from back page {i+1}")
                
                # Try to find identifiers in back matter using centralized function
                back_identifiers = utils_extract_identifiers(back_pages_text)
                if not doi:
                    doi = back_identifiers['doi']
                if not isbn:
                    isbn = back_identifiers['isbn']
            
            # Important: Close document at the end
            total_pages = len(doc)
            doc.close()
            doc = None
            
            result = {
                'doi': doi,
                'isbn': isbn,
                'pages_processed': pages_to_process,
                'total_pages': total_pages
            }
            logger.info(f"Identifier extraction complete: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting identifiers: {e}", exc_info=True)
            return {'error': str(e)}
        finally:
            # Ensure document is closed
            if doc:
                try:
                    doc.close()
                    logger.debug("Closed PDF document in finally block")
                except Exception as e:
                    logger.error(f"Error closing document in finally block: {e}")
    
    def cleanup_cache(self):
        """Clean up internal cache"""
        self._identifier_cache.clear()