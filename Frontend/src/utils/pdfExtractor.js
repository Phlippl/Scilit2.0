// Frontend/src/utils/pdfExtractor.js
import * as pdfjs from 'pdfjs-dist';
import { createWorker } from 'tesseract.js';

// Set PDF.js worker source
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

/**
 * Utility class for extracting identifiers (DOI, ISBN) from PDF documents
 */
class PDFExtractor {
  /**
   * Extracts text from a PDF file
   * @param {File|Blob} pdfFile - The PDF file
   * @param {number} maxPages - Maximum pages to scan (default: first 10 pages)
   * @returns {Promise<string>} - Promise resolving to extracted text
   */
  async extractText(pdfFile, maxPages = 10) {
    try {
      const arrayBuffer = await pdfFile.arrayBuffer();
      const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
      
      // Limit to first few pages for efficiency
      const pageCount = Math.min(pdf.numPages, maxPages);
      let fullText = '';
      
      // Extract text from each page
      for (let i = 1; i <= pageCount; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        const pageText = textContent.items.map(item => item.str).join(' ');
        fullText += pageText + ' ';
      }
      
      return fullText;
    } catch (error) {
      console.error('Error extracting text from PDF:', error);
      throw error;
    }
  }
  
  /**
   * Use OCR to extract text from PDF if needed
   * @param {File|Blob} pdfFile - The PDF file
   * @returns {Promise<string>} - Promise resolving to OCR extracted text
   */
  async performOCR(pdfFile) {
    try {
      // Create Tesseract worker
      const worker = await createWorker('eng');
      
      // Convert PDF to image using PDF.js and canvas
      const arrayBuffer = await pdfFile.arrayBuffer();
      const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
      
      // Process only first few pages
      const pageCount = Math.min(pdf.numPages, 3);
      let ocrText = '';
      
      for (let i = 1; i <= pageCount; i++) {
        const page = await pdf.getPage(i);
        const viewport = page.getViewport({ scale: 1.5 }); // Higher scale for better OCR
        
        // Create canvas for rendering
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        
        // Render PDF page to canvas
        await page.render({
          canvasContext: context,
          viewport: viewport
        }).promise;
        
        // Convert canvas to blob
        const blob = await new Promise(resolve => {
          canvas.toBlob(resolve, 'image/png');
        });
        
        // Perform OCR on the image
        const { data } = await worker.recognize(blob);
        ocrText += data.text + ' ';
      }
      
      await worker.terminate();
      return ocrText;
    } catch (error) {
      console.error('Error performing OCR:', error);
      throw error;
    }
  }

  /**
   * Extract DOI from text using regex patterns
   * @param {string} text - Text to search for DOI
   * @returns {string|null} - Extracted DOI or null if not found
   */
  extractDOI(text) {
    if (!text) return null;
    
    // DOI regex pattern
    // Format: 10.XXXX/XXXXX
    const doiPattern = /\b(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&'<>])\S)+)\b/i;
    const matches = text.match(doiPattern);
    
    return matches ? matches[1] : null;
  }
  
  /**
   * Extract ISBN from text using regex patterns
   * @param {string} text - Text to search for ISBN
   * @returns {string|null} - Extracted ISBN or null if not found
   */
  extractISBN(text) {
    if (!text) return null;
    
    // ISBN-10 and ISBN-13 regex patterns
    const isbn10Pattern = /\bISBN(?:-10)?[:\s]*([\d\-]{10,})/i;
    const isbn13Pattern = /\bISBN(?:-13)?[:\s]*([\d\-]{13,})/i;
    
    // Try ISBN-13 first, then ISBN-10
    const matches13 = text.match(isbn13Pattern);
    if (matches13) {
      return matches13[1].replace(/[-\s]/g, '');
    }
    
    const matches10 = text.match(isbn10Pattern);
    if (matches10) {
      return matches10[1].replace(/[-\s]/g, '');
    }
    
    return null;
  }
  
  /**
   * Process a PDF file to extract DOI and ISBN
   * @param {File} file - The PDF file
   * @returns {Promise<Object>} - Promise resolving to extracted identifiers
   */
  async processFile(file) {
    try {
      // First try extracting text directly
      let text = await this.extractText(file);
      let doi = this.extractDOI(text);
      let isbn = this.extractISBN(text);
      
      // If no identifiers found and file is less than 10MB, try OCR
      // (limiting file size to avoid performance issues)
      if ((!doi && !isbn) && file.size < 10 * 1024 * 1024) {
        console.log('No identifiers found in text, trying OCR...');
        const ocrText = await this.performOCR(file);
        doi = doi || this.extractDOI(ocrText);
        isbn = isbn || this.extractISBN(ocrText);
      }
      
      return { doi, isbn, text };
    } catch (error) {
      console.error('Error processing PDF file:', error);
      throw error;
    }
  }
}

export default new PDFExtractor();