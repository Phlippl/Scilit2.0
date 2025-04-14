# services/pdf_processor.py
import os
import re
import logging
import tempfile
import pytesseract
from PIL import Image
import io
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import fitz  # PyMuPDF
import spacy
import time
import langdetect
import gc

logger = logging.getLogger(__name__)

# Mehrsprachiges spaCy-Setup mit Fallback
def load_spacy_model(language='en'):
    try:
        if language == 'de':
            return spacy.load("de_core_news_sm")
        else:
            return spacy.load("en_core_web_sm")
    except OSError:
        logger.warning("spaCy model not found. Using blank model.")
        return spacy.blank(language)

class PDFProcessor:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.ocr_executor = ThreadPoolExecutor(max_workers=1)

    def extract_text_from_pdf(self, file_path: str, perform_ocr=True, progress_callback=None) -> Dict:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        all_text = ""
        pages_info = []
        ocr_pages = []

        for i, page in enumerate(doc):
            page_text = page.get_text()
            if len(page_text.strip()) < 100 and perform_ocr:
                ocr_pages.append(i)
                page_text = ""
            pages_info.append({
                "pageNumber": i + 1,
                "text": page_text,
                "startPosition": len(all_text)
            })
            all_text += page_text + "\n"
            if progress_callback:
                progress_callback(f"Seite {i+1}/{total_pages} geladen", int((i + 1) / total_pages * 30))

        # OCR separat behandeln
        if ocr_pages:
            ocr_results = {}
            for idx in ocr_pages:
                if progress_callback:
                    progress_callback(f"OCR für Seite {idx+1}", 30 + int((idx + 1) / total_pages * 20))
                ocr_results[idx] = self._perform_ocr_on_page(doc[idx])
                pages_info[idx]['text'] = ocr_results[idx]
                all_text += ocr_results[idx] + "\n"

        # Endpositionen setzen
        current_pos = 0
        for page in pages_info:
            page_len = len(page['text'])
            page['startPosition'] = current_pos
            page['endPosition'] = current_pos + page_len
            current_pos += page_len

        doc.close()
        return {
            "text": all_text,
            "pages": pages_info,
            "totalPages": total_pages
        }

    def _perform_ocr_on_page(self, page, dpi=300):
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
        image_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(image_data))
        return pytesseract.image_to_string(image)

    def extract_doi(self, text: str) -> Optional[str]:
        match = re.search(r'\b(10\.\d{4,}(?:\.\d+)*\/[^\s"<>]+)', text)
        return match.group(1) if match else None

    def extract_isbn(self, text: str) -> Optional[str]:
        match = re.search(r'\b(?:ISBN[- ]*(1[03])?:? )?(97(8|9))?\d{9}(\d|X)\b', text)
        return match.group(0).replace('-', '').replace(' ', '') if match else None

    def chunk_text_semantic(self, text: str, pages_info: List[Dict[str, Any]], language='en', progress_callback=None) -> List[Dict[str, Any]]:
        if progress_callback:
            progress_callback("Starte semantisches Chunking...", 60)

        if not text.strip():
            return []

        # spaCy laden (Sprache automatisch wählen)
        try:
            detected_lang = langdetect.detect(text[:1000])
        except:
            detected_lang = language

        nlp = load_spacy_model('de' if detected_lang == 'de' else 'en')

        # chunk-größe hier irrelevant, Fokus auf Sinnabschnitte
        chunks = []
        current_chunk = []
        current_text_len = 0

        # spaCy Verarbeitung
        try:
            doc = nlp(text)
            for sent in doc.sents:
                sentence = sent.text.strip()
                if not sentence:
                    continue
                current_chunk.append(sentence)
                current_text_len += len(sentence)
                if current_text_len >= 1500:  # Chunk bei ca. 1500 Zeichen abschließen
                    combined = " ".join(current_chunk)
                    page = self._infer_page(combined, pages_info)
                    chunks.append({
                        "text": combined,
                        "page_number": page
                    })
                    current_chunk = []
                    current_text_len = 0
            if current_chunk:
                combined = " ".join(current_chunk)
                page = self._infer_page(combined, pages_info)
                chunks.append({
                    "text": combined,
                    "page_number": page
                })
        except Exception as e:
            logger.error(f"Fehler beim Chunking mit spaCy: {e}")
            # Fallback auf grobe Aufteilung
            fallback_chunks = re.split(r'\n\s*\n', text)
            for chunk in fallback_chunks:
                page = self._infer_page(chunk, pages_info)
                chunks.append({
                    "text": chunk.strip(),
                    "page_number": page
                })

        if progress_callback:
            progress_callback("Chunking abgeschlossen", 90)

        return chunks

    def _infer_page(self, chunk_text: str, pages_info: List[Dict[str, Any]]) -> int:
        """Ermittelt anhand der Position im Text die wahrscheinliche Seitenzahl"""
        for page in pages_info:
            if chunk_text[:50] in page['text']:
                return page['pageNumber']
        return 1  # Default

    def process_file(self, file_path: str, settings: Optional[Dict[str, Any]] = None, progress_callback=None) -> Dict:
        if settings is None:
            settings = {
                "performOCR": True
            }

        try:
            if progress_callback:
                progress_callback("PDF wird geöffnet...", 5)

            result = self.extract_text_from_pdf(
                file_path,
                perform_ocr=settings.get("performOCR", True),
                progress_callback=progress_callback
            )

            if progress_callback:
                progress_callback("Extrahiere Metadaten (DOI/ISBN)...", 50)

            doi = self.extract_doi(result["text"])
            isbn = self.extract_isbn(result["text"])

            chunks = self.chunk_text_semantic(
                result["text"],
                result["pages"],
                progress_callback=progress_callback
            )

            if progress_callback:
                progress_callback("Datei vollständig verarbeitet", 100)

            return {
                "text": result["text"],
                "chunks": chunks,
                "metadata": {
                    "doi": doi,
                    "isbn": isbn,
                    "totalPages": result["totalPages"]
                },
                "pages": result["pages"]
            }

        except Exception as e:
            logger.error(f"Fehler bei der PDF-Verarbeitung: {e}", exc_info=True)
            raise RuntimeError(f"Fehler beim Verarbeiten der PDF: {e}")
