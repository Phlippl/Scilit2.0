// src/services/pdfService.js
import * as pdfjs from 'pdfjs-dist';
import { createWorker } from 'tesseract.js';

// Set PDF.js worker source
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

/**
 * Comprehensive PDF Processing service with text extraction, OCR, metadata extraction and chunking
 */
class PDFService {
  /**
   * Extracts text from a PDF file with progress reporting
   * @param {File|Blob} pdfFile - The PDF file
   * @param {Object} options - Extraction options
   * @param {number} options.maxPages - Maximum pages to scan (0 = all pages)
   * @param {Function} options.progressCallback - Progress callback function (0-100)
   * @returns {Promise<Object>} - Promise resolving to extracted text and page info
   */
  async extractText(pdfFile, options = {}) {
    const {
      maxPages = 0,
      progressCallback = null
    } = options;
    
    try {
      // Report progress
      if (progressCallback) {
        progressCallback('Loading PDF...', 0);
      }
      
      const arrayBuffer = await pdfFile.arrayBuffer();
      const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
      
      // If maxPages is 0 or higher than actual, process all pages
      const pageCount = pdf.numPages;
      const pagesToProcess = maxPages > 0 ? Math.min(pageCount, maxPages) : pageCount;
      
      // Prepare result object
      const result = {
        text: '',
        pages: [],
        totalPages: pageCount,
        processedPages: pagesToProcess
      };
      
      // Extract text from each page
      for (let i = 1; i <= pagesToProcess; i++) {
        // Report progress
        if (progressCallback) {
          progressCallback(
            `Processing page ${i} of ${pagesToProcess}...`, 
            Math.round((i - 1) / pagesToProcess * 100)
          );
        }
        
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        
        // Get page dimensions for metadata
        const viewport = page.getViewport({ scale: 1.0 });
        
        // Extract text
        const pageText = textContent.items.map(item => item.str).join(' ');
        
        // Add to results
        result.text += pageText + ' ';
        result.pages.push({
          pageNumber: i,
          text: pageText,
          width: viewport.width,
          height: viewport.height
        });
      }
      
      // Final progress report
      if (progressCallback) {
        progressCallback('Text extraction complete', 100);
      }
      
      return result;
    } catch (error) {
      console.error('Error extracting text from PDF:', error);
      throw new Error(`PDF text extraction failed: ${error.message}`);
    }
  }
  
  /**
   * Perform OCR on PDF pages that have little or no text content
   * @param {File|Blob} pdfFile - The PDF file
   * @param {Array} pageNumbers - Page numbers to process (1-based indexing)
   * @param {Function} progressCallback - Progress callback
   * @returns {Promise<Object>} - Promise resolving to OCR results
   */
  async performOCR(pdfFile, pageNumbers = [], progressCallback = null) {
    try {
      // Initialize Tesseract worker
      const worker = await createWorker('eng');
      
      // Convert PDF to image and perform OCR
      const arrayBuffer = await pdfFile.arrayBuffer();
      const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
      
      // Default to first 3 pages if none specified
      const pagesToProcess = pageNumbers.length > 0 
        ? pageNumbers 
        : Array.from({ length: Math.min(pdf.numPages, 3) }, (_, i) => i + 1);
      
      const results = [];
      
      for (let i = 0; i < pagesToProcess.length; i++) {
        const pageNumber = pagesToProcess[i];
        const page = await pdf.getPage(pageNumber);
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
        
        results.push({
          pageNumber,
          text: data.text
        });
        
        // Report progress
        if (progressCallback) {
          progressCallback(Math.round((i + 1) / pagesToProcess.length * 100));
        }
      }
      
      await worker.terminate();
      
      return {
        ocrResults: results,
        combinedText: results.map(r => r.text).join(' ')
      };
    } catch (error) {
      console.error('Error performing OCR:', error);
      throw new Error(`OCR processing failed: ${error.message}`);
    }
  }

  /**
   * Extract DOI from text using regex patterns
   * @param {string} text - Text to search for DOI
   * @returns {string|null} - Extracted DOI or null if not found
   */
  extractDOI(text) {
    if (!text) return null;
    
    // DOI regex pattern - improved for better matching
    // Format: 10.XXXX/XXXXX
    const doiPatterns = [
      /\b(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&'<>])\S)+)\b/i,
      /\bDOI:\s*(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&'<>])\S)+)\b/i,
      /\bdoi\.org\/(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&'<>])\S)+)\b/i
    ];
    
    for (const pattern of doiPatterns) {
      const matches = text.match(pattern);
      if (matches && matches[1]) {
        return matches[1];
      }
    }
    
    return null;
  }
  
  /**
   * Extract ISBN from text using regex patterns
   * @param {string} text - Text to search for ISBN
   * @returns {string|null} - Extracted ISBN or null if not found
   */
  extractISBN(text) {
    if (!text) return null;
    
    // ISBN-10 and ISBN-13 regex patterns - improved for better matching
    const isbnPatterns = [
      /\bISBN(?:-13)?[:\s]*(97[89][- ]?(?:\d[- ]?){9}\d)\b/i,  // ISBN-13
      /\bISBN(?:-10)?[:\s]*(\d[- ]?(?:\d[- ]?){8}[\dX])\b/i,   // ISBN-10
      /\b(97[89][- ]?(?:\d[- ]?){9}\d)\b/i,  // Bare ISBN-13
      /\b(\d[- ]?(?:\d[- ]?){8}[\dX])\b/i    // Bare ISBN-10
    ];
    
    for (const pattern of isbnPatterns) {
      const matches = text.match(pattern);
      if (matches && matches[1]) {
        // Clean up and normalize ISBN format
        return matches[1].replace(/[-\s]/g, '');
      }
    }
    
    return null;
  }
  
  /**
   * Split document text into smaller chunks with configurable size and overlap
   * @param {string} text - Full document text
   * @param {number} chunkSize - Target chunk size in characters
   * @param {number} overlapSize - Overlap size in characters
   * @returns {Array} - Array of text chunks
   */
  chunkText(text, chunkSize = 1000, overlapSize = 200) {
    if (!text || chunkSize <= 0) {
      return [];
    }
    
    const chunks = [];
    
    // If text is smaller than chunk size, return as single chunk
    if (text.length <= chunkSize) {
      return [text];
    }
    
    let startIndex = 0;
    
    while (startIndex < text.length) {
      // Calculate end index based on chunk size
      let endIndex = startIndex + chunkSize;
      
      // If we're at the end of the text, just use the remaining text
      if (endIndex >= text.length) {
        chunks.push(text.substring(startIndex));
        break;
      }
      
      // Try to find a natural break point (sentence or paragraph end)
      const naturalBreakIndex = this.findNaturalBreakPoint(text, endIndex);
      
      // Add chunk using the natural break point
      chunks.push(text.substring(startIndex, naturalBreakIndex));
      
      // Move start index to next chunk, accounting for overlap
      startIndex = naturalBreakIndex - overlapSize;
      
      // Ensure we're not going backward
      if (startIndex < 0 || startIndex <= chunks.length) {
        startIndex = naturalBreakIndex;
      }
    }
    
    return chunks;
  }
  
  /**
   * Find a natural break point (end of sentence or paragraph) near the target index
   * @param {string} text - Text to analyze
   * @param {number} targetIndex - Target index
   * @returns {number} - Index of the natural break point
   */
  findNaturalBreakPoint(text, targetIndex) {
    // Try to find paragraph break within ±100 characters of target
    const paragraphSearchRange = 100;
    const paragraphStart = Math.max(0, targetIndex - paragraphSearchRange);
    const paragraphEnd = Math.min(text.length, targetIndex + paragraphSearchRange);
    
    const paragraphBreakSearch = text.substring(paragraphStart, paragraphEnd);
    
    // Look for double newline (paragraph break)
    const paragraphMatch = paragraphBreakSearch.match(/\n\s*\n/);
    
    if (paragraphMatch) {
      const matchIndex = paragraphMatch.index + paragraphStart;
      // Ensure we're after the target index or reasonably close
      if (matchIndex > targetIndex - 50) {
        return matchIndex;
      }
    }
    
    // Try to find sentence end within ±50 characters of target
    const sentenceSearchRange = 50;
    const sentenceStart = Math.max(0, targetIndex - sentenceSearchRange);
    const sentenceEnd = Math.min(text.length, targetIndex + sentenceSearchRange);
    
    const sentenceBreakSearch = text.substring(sentenceStart, sentenceEnd);
    
    // Look for sentence end (period, question mark, exclamation mark followed by space)
    const sentenceMatch = sentenceBreakSearch.match(/[.!?]\s/);
    
    if (sentenceMatch) {
      return sentenceMatch.index + sentenceStart + 2; // +2 to include the space
    }
    
    // Fallback: Look for the nearest space after the target index
    const spaceAfter = text.indexOf(' ', targetIndex);
    
    if (spaceAfter !== -1) {
      return spaceAfter + 1; // +1 to skip the space
    }
    
    // If all else fails, just use the target index
    return targetIndex;
  }
  
  /**
   * Process a PDF file to extract metadata, text, and chunks
   * @param {File} file - The PDF file
   * @param {Object} options - Processing options
   * @returns {Promise<Object>} - Promise resolving to processing results
   */
  async processFile(file, options = {}) {
    const {
      maxPages = 0,
      chunkSize = 1000,
      chunkOverlap = 200,
      performOCR = false,
      progressCallback = null
    } = options;
    
    try {
      // Progress reporting helper
      const reportProgress = (stage, percent) => {
        if (progressCallback) {
          progressCallback(stage, percent);
        }
      };
      
      reportProgress('Extracting text from PDF...', 0);
      
      // Extract text from the PDF
      const extractionResult = await this.extractText(
        file, 
        {
          maxPages,
          progressCallback: (message, percent) => reportProgress(message, percent)
        }
      );
      
      // Extract identifiers
      reportProgress('Extracting metadata...', 0);
      let doi = this.extractDOI(extractionResult.text);
      let isbn = this.extractISBN(extractionResult.text);
      
      // If no text was found or identifiers couldn't be extracted, try OCR if enabled
      let ocrText = '';
      if (performOCR && ((!doi && !isbn) || extractionResult.text.trim().length < 100)) {
        reportProgress('Performing OCR processing...', 0);
        
        // Only process first few pages to save time
        const ocrResult = await this.performOCR(
          file,
          [1, 2, 3], // First 3 pages
          (percent) => reportProgress('Performing OCR processing...', percent)
        );
        
        ocrText = ocrResult.combinedText;
        
        // Try to extract identifiers from OCR text
        doi = doi || this.extractDOI(ocrText);
        isbn = isbn || this.extractISBN(ocrText);
        
        reportProgress('OCR processing complete', 100);
      }
      
      // Combine extracted text and OCR text
      const fullText = extractionResult.text + ' ' + ocrText;
      
      // Create chunks
      reportProgress('Creating text chunks...', 0);
      const chunks = this.chunkText(fullText, chunkSize, chunkOverlap);
      reportProgress('Processing complete', 100);
      
      return {
        fileName: file.name,
        fileSize: file.size,
        pageCount: extractionResult.totalPages,
        processedPages: extractionResult.processedPages,
        metadata: {
          doi,
          isbn
        },
        text: fullText,
        chunks,
        pages: extractionResult.pages
      };
    } catch (error) {
      console.error('Error processing PDF file:', error);
      throw error;
    }
  }
}

export default new PDFService();