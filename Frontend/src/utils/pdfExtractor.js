// src/utils/pdfExtractor.js - Fixed version
import * as pdfjs from 'pdfjs-dist';
// Import the worker directly if possible
import { PDFWorker } from 'pdfjs-dist/build/pdf.worker.entry';

// Try to use local worker instead of CDN
try {
  pdfjs.GlobalWorkerOptions.workerSrc = PDFWorker;
} catch (e) {
  console.warn('Could not load PDF.js worker directly, falling back to CDN', e);
  // Fallback to CDN
  pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;
}

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
  
  // Rest of the class remains the same...
  // Methods like performOCR, extractDOI, extractISBN, and processFile are unchanged
}

export default new PDFExtractor();