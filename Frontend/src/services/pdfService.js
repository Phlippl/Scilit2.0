// src/services/pdfService.js
import * as pdfjs from 'pdfjs-dist';
import { PDFWorker } from 'pdfjs-dist/build/pdf.worker.entry';

// Worker-Konfiguration
try {
  pdfjs.GlobalWorkerOptions.workerSrc = PDFWorker;
} catch (e) {
  console.warn('PDF.js Worker konnte nicht direkt geladen werden, Fallback zu CDN', e);
  pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;
}

/**
 * Service für PDF-Verarbeitung mit Extraktion von Text, DOI und ISBN
 */
class PDFService {
  /**
   * Extrahiert Text aus einer PDF-Datei
   * 
   * @param {File|Blob} pdfFile - Die PDF-Datei
   * @param {Object} options - Optionen für die Extraktion
   * @param {number} options.maxPages - Maximale Seitenzahl (0 = alle Seiten)
   * @param {Function} options.progressCallback - Callback für Fortschrittsmeldungen
   * @returns {Promise<Object>} - Promise mit dem extrahierten Text und Metadaten
   */
  async extractText(pdfFile, options = {}) {
    const {
      maxPages = 0,
      progressCallback = null
    } = options;
    
    try {
      // Fortschritt melden
      if (progressCallback) {
        progressCallback('Lade PDF...', 0);
      }
      
      const arrayBuffer = await pdfFile.arrayBuffer();
      const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
      
      // Bei maxPages 0 oder höher als tatsächlich, alle Seiten verarbeiten
      const pageCount = pdf.numPages;
      const pagesToProcess = maxPages > 0 ? Math.min(pageCount, maxPages) : pageCount;
      
      // Ergebnisobjekt vorbereiten
      const result = {
        text: '',
        pages: [],
        totalPages: pageCount,
        processedPages: pagesToProcess
      };
      
      // Text von jeder Seite extrahieren
      for (let i = 1; i <= pagesToProcess; i++) {
        // Fortschritt melden
        if (progressCallback) {
          progressCallback(
            `Verarbeite Seite ${i} von ${pagesToProcess}...`, 
            Math.round((i - 1) / pagesToProcess * 100)
          );
        }
        
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        
        // Seitenabmessungen für Metadaten
        const viewport = page.getViewport({ scale: 1.0 });
        
        // Text extrahieren
        const pageText = textContent.items.map(item => item.str).join(' ');
        
        // Zu Ergebnissen hinzufügen
        result.text += pageText + ' ';
        result.pages.push({
          pageNumber: i,
          text: pageText,
          width: viewport.width,
          height: viewport.height
        });
      }
      
      // Abschluss-Fortschritt melden
      if (progressCallback) {
        progressCallback('Textextraktion abgeschlossen', 100);
      }
      
      return result;
    } catch (error) {
      console.error('Fehler bei der Textextraktion aus PDF:', error);
      throw new Error(`PDF-Textextraktion fehlgeschlagen: ${error.message}`);
    }
  }
  
  /**
   * Extrahiert DOI aus Text mittels Regex-Mustern
   * 
   * @param {string} text - Zu durchsuchender Text
   * @returns {string|null} - Extrahierte DOI oder null, wenn nicht gefunden
   */
  extractDOI(text) {
    if (!text) return null;
    
    // DOI-Regex-Muster - verbessert für bessere Trefferquote
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
   * Extrahiert ISBN aus Text mittels Regex-Mustern
   * 
   * @param {string} text - Zu durchsuchender Text
   * @returns {string|null} - Extrahierte ISBN oder null, wenn nicht gefunden
   */
  extractISBN(text) {
    if (!text) return null;
    
    // ISBN-10 und ISBN-13 Regex-Muster
    const isbnPatterns = [
      /\bISBN(?:-13)?[:\s]*(97[89][- ]?(?:\d[- ]?){9}\d)\b/i,  // ISBN-13
      /\bISBN(?:-10)?[:\s]*(\d[- ]?(?:\d[- ]?){8}[\dX])\b/i,   // ISBN-10
      /\b(97[89][- ]?(?:\d[- ]?){9}\d)\b/i,  // Nackte ISBN-13
      /\b(\d[- ]?(?:\d[- ]?){8}[\dX])\b/i    // Nackte ISBN-10
    ];
    
    for (const pattern of isbnPatterns) {
      const matches = text.match(pattern);
      if (matches && matches[1]) {
        // ISBN-Format bereinigen und normalisieren
        return matches[1].replace(/[-\s]/g, '');
      }
    }
    
    return null;
  }
  
  /**
   * Teilt Dokumenttext in kleinere Chunks mit konfigurierbarer Größe und Überlappung
   * 
   * @param {string} text - Vollständiger Dokumenttext
   * @param {number} chunkSize - Zielgröße der Chunks in Zeichen
   * @param {number} overlapSize - Überlappungsgröße in Zeichen
   * @returns {Array} - Array von Textchunks
   */
  chunkText(text, chunkSize = 1000, overlapSize = 200) {
    if (!text || chunkSize <= 0) {
      return [];
    }
    
    const chunks = [];
    
    // Wenn Text kleiner als Chunk-Größe, als einzelnen Chunk zurückgeben
    if (text.length <= chunkSize) {
      return [text];
    }
    
    let startIndex = 0;
    
    while (startIndex < text.length) {
      // End-Index basierend auf Chunk-Größe berechnen
      let endIndex = startIndex + chunkSize;
      
      // Wenn wir am Ende des Textes sind, einfach den restlichen Text verwenden
      if (endIndex >= text.length) {
        chunks.push(text.substring(startIndex));
        break;
      }
      
      // Versuche, einen natürlichen Breakpoint (Satz- oder Absatzende) zu finden
      const naturalBreakIndex = this.findNaturalBreakPoint(text, endIndex);
      
      // Chunk hinzufügen mit dem natürlichen Breakpoint
      chunks.push(text.substring(startIndex, naturalBreakIndex));
      
      // Start-Index für nächsten Chunk verschieben, unter Berücksichtigung der Überlappung
      startIndex = naturalBreakIndex - overlapSize;
      
      // Sicherstellen, dass wir nicht rückwärts gehen
      if (startIndex < 0 || startIndex <= chunks.length) {
        startIndex = naturalBreakIndex;
      }
    }
    
    return chunks;
  }
  
  /**
   * Findet einen natürlichen Breakpoint (Satz- oder Absatzende) nahe dem Zielindex
   * 
   * @param {string} text - Zu analysierender Text
   * @param {number} targetIndex - Zielindex
   * @returns {number} - Index des natürlichen Breakpoints
   */
  findNaturalBreakPoint(text, targetIndex) {
    // Versuche, einen Absatzumbruch innerhalb von ±100 Zeichen des Ziels zu finden
    const paragraphSearchRange = 100;
    const paragraphStart = Math.max(0, targetIndex - paragraphSearchRange);
    const paragraphEnd = Math.min(text.length, targetIndex + paragraphSearchRange);
    
    const paragraphBreakSearch = text.substring(paragraphStart, paragraphEnd);
    
    // Suche nach doppeltem Zeilenumbruch (Absatzumbruch)
    const paragraphMatch = paragraphBreakSearch.match(/\n\s*\n/);
    
    if (paragraphMatch) {
      const matchIndex = paragraphMatch.index + paragraphStart;
      // Stellen Sie sicher, dass wir nach dem Zielindex oder angemessen nahe sind
      if (matchIndex > targetIndex - 50) {
        return matchIndex;
      }
    }
    
    // Versuche, ein Satzende innerhalb von ±50 Zeichen des Ziels zu finden
    const sentenceSearchRange = 50;
    const sentenceStart = Math.max(0, targetIndex - sentenceSearchRange);
    const sentenceEnd = Math.min(text.length, targetIndex + sentenceSearchRange);
    
    const sentenceBreakSearch = text.substring(sentenceStart, sentenceEnd);
    
    // Suche nach Satzende (Punkt, Fragezeichen, Ausrufezeichen gefolgt von Leerzeichen)
    const sentenceMatch = sentenceBreakSearch.match(/[.!?]\s/);
    
    if (sentenceMatch) {
      return sentenceMatch.index + sentenceStart + 2; // +2 um das Leerzeichen einzuschließen
    }
    
    // Fallback: Suche nach dem nächsten Leerzeichen nach dem Zielindex
    const spaceAfter = text.indexOf(' ', targetIndex);
    
    if (spaceAfter !== -1) {
      return spaceAfter + 1; // +1 um das Leerzeichen zu überspringen
    }
    
    // Wenn alles andere fehlschlägt, einfach den Zielindex verwenden
    return targetIndex;
  }
  
  /**
   * Verarbeitet eine PDF-Datei, um Metadaten, Text und Chunks zu extrahieren
   * 
   * @param {File} file - Die PDF-Datei
   * @param {Object} options - Verarbeitungsoptionen
   * @returns {Promise<Object>} - Promise mit Verarbeitungsergebnissen
   */
  async processFile(file, options = {}) {
    const {
      maxPages = 0,
      chunkSize = 1000,
      chunkOverlap = 200,
      progressCallback = null
    } = options;
    
    try {
      // Fortschrittsberichts-Helfer
      const reportProgress = (stage, percent) => {
        if (progressCallback) {
          progressCallback(stage, percent);
        }
      };
      
      reportProgress('Extrahiere Text aus PDF...', 0);
      
      // Text aus dem PDF extrahieren
      const extractionResult = await this.extractText(
        file, 
        {
          maxPages,
          progressCallback: (message, percent) => reportProgress(message, percent)
        }
      );
      
      // Identifikatoren extrahieren
      reportProgress('Extrahiere Metadaten...', 0);
      const doi = this.extractDOI(extractionResult.text);
      const isbn = this.extractISBN(extractionResult.text);
      
      reportProgress('Erstelle Text-Chunks...', 0);
      
      // Chunks erstellen
      const chunks = this.chunkText(extractionResult.text, chunkSize, chunkOverlap);
      reportProgress('Verarbeitung abgeschlossen', 100);
      
      return {
        fileName: file.name,
        fileSize: file.size,
        pageCount: extractionResult.totalPages,
        processedPages: extractionResult.processedPages,
        metadata: {
          doi,
          isbn
        },
        text: extractionResult.text,
        chunks,
        pages: extractionResult.pages
      };
    } catch (error) {
      console.error('Fehler bei der Verarbeitung der PDF-Datei:', error);
      throw error;
    }
  }
}

export default new PDFService();