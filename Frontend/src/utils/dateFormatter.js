// src/utils/dateFormatter.js

/**
 * Formatiert ein Datum in das ISO-Format YYYY-MM-DD
 * 
 * @param {string|Date} date - Zu formatierendes Datum
 * @returns {string} - Formatiertes Datum im Format YYYY-MM-DD
 */
export const formatToISODate = (date) => {
    if (!date) return '';
    
    try {
      // Wenn das Datum bereits im ISO-Format ist (YYYY-MM-DD)
      if (typeof date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
        return date;
      }
      
      // Wenn nur das Jahr angegeben ist (YYYY)
      if (typeof date === 'string' && /^\d{4}$/.test(date)) {
        return `${date}-01-01`;
      }
      
      // Wenn das Datum im Format DD.MM.YYYY ist
      if (typeof date === 'string' && /^\d{1,2}\.\d{1,2}\.\d{4}$/.test(date)) {
        const parts = date.split('.');
        return `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
      }
  
      // Wenn Datum im Format MM/DD/YYYY ist
      if (typeof date === 'string' && /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(date)) {
        const parts = date.split('/');
        return `${parts[2]}-${parts[0].padStart(2, '0')}-${parts[1].padStart(2, '0')}`;
      }
      
      // Andere Datumsformate wie "3 Nov 2015" oder "Nov 3, 2015"
      const dateObj = new Date(date);
      if (!isNaN(dateObj.getTime())) {
        return dateObj.toISOString().split('T')[0];
      }
      
      // Wenn nichts funktioniert, versuche nach Jahr-Monat-Tag-Muster zu parsen
      const yearMatch = typeof date === 'string' && date.match(/(\d{4})/);
      if (yearMatch) {
        const year = yearMatch[1];
        
        // Monat suchen (Zahl oder Name)
        let month = '01';
        const monthMatch = date.match(/(\d{1,2})[\/\-\.]/) || 
                           date.match(/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i);
        if (monthMatch) {
          if (/^\d+$/.test(monthMatch[0])) {
            month = monthMatch[0].padStart(2, '0');
          } else {
            // Monatsnamen in Zahl umwandeln
            const monthNames = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
            const monthIndex = monthNames.findIndex(m => 
              monthMatch[0].toLowerCase().startsWith(m));
            if (monthIndex >= 0) {
              month = String(monthIndex + 1).padStart(2, '0');
            }
          }
        }
        
        // Tag suchen
        let day = '01';
        const dayMatch = date.match(/(\d{1,2})(?!\d{2})(?:[\/\-\.]|\s+)/);
        if (dayMatch) {
          day = dayMatch[1].padStart(2, '0');
        }
        
        return `${year}-${month}-${day}`;
      }
      
      // Wenn nichts funktioniert hat
      return '';
    } catch (error) {
      console.error('Fehler bei der Datumsformatierung:', error);
      return '';
    }
  };
  
  /**
   * Wandelt Datum aus ISO-Format (YYYY-MM-DD) in lokalisiertes Format um
   * 
   * @param {string} isoDate - Datum im ISO-Format
   * @param {string} locale - Locale für Formatierung (default: 'de-DE')
   * @returns {string} - Formatiertes Datum
   */
  export const formatFromISODate = (isoDate, locale = 'de-DE') => {
    if (!isoDate) return '';
    
    try {
      const date = new Date(isoDate);
      if (isNaN(date.getTime())) return isoDate;
      
      return date.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch (error) {
      console.error('Fehler bei der Datumsformatierung:', error);
      return isoDate;
    }
  };
  
  export default {
    formatToISODate,
    formatFromISODate
  };