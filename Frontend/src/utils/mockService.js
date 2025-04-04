// src/utils/mockService.js

/**
 * Mock-Service für Testumgebung
 * Stellt Fake-Daten bereit, wenn VITE_TEST_USER_ENABLED=true gesetzt ist
 */

// Beispiel-Dokumente für die Testumgebung
const mockDocuments = [
    {
      id: "doc1",
      title: "Climate Change Effects on Agricultural Systems",
      authors: [
        { name: "Smith, John", orcid: "0000-0001-2345-6789" },
        { name: "Johnson, Maria", orcid: "0000-0002-3456-7890" }
      ],
      type: "article",
      publicationDate: "2023-04-15",
      journal: "Journal of Environmental Science",
      doi: "10.1234/jes.2023.01.001",
      publisher: "Academic Press",
      uploadDate: "2024-04-01T12:30:45Z",
      abstract: "This paper examines the impact of climate change on agricultural systems worldwide...",
    },
    {
      id: "doc2",
      title: "Machine Learning Applications in Medicine",
      authors: [
        { name: "Brown, Robert", orcid: "0000-0003-4567-8901" },
        { name: "Davis, Sarah", orcid: "0000-0004-5678-9012" }
      ],
      type: "article",
      publicationDate: "2023-08-22",
      journal: "Medical Informatics Journal",
      doi: "10.5678/mij.2023.02.005",
      publisher: "Medical Science Publications",
      uploadDate: "2024-04-02T09:15:30Z",
      abstract: "This review explores the current and future applications of machine learning in clinical settings...",
    },
    {
      id: "doc3",
      title: "Fundamentals of Quantum Computing",
      authors: [
        { name: "Wilson, Thomas", orcid: "0000-0005-6789-0123" }
      ],
      type: "book",
      publicationDate: "2022-11-10",
      isbn: "978-3-16-148410-0",
      publisher: "Tech Academic Press",
      uploadDate: "2024-04-03T14:45:20Z",
      abstract: "This book provides a comprehensive introduction to quantum computing principles...",
    }
  ];
  
  // Beispiel-Suchanfragen und -Ergebnisse
  const mockQueryResults = {
    "climate change agriculture": {
      results: [
        {
          text: "Climate change has been shown to significantly impact crop yields in temperate regions, with decreases of up to 15% observed in long-term studies.",
          source: "Smith, J., & Johnson, M. (2023, S. 42)"
        },
        {
          text: "Adaptation strategies for agricultural systems include crop diversification, modified planting schedules, and the development of drought-resistant varieties.",
          source: "Smith, J., & Johnson, M. (2023, S. 45)"
        }
      ],
      bibliography: [
        "Smith, J., & Johnson, M. (2023). Climate Change Effects on Agricultural Systems. Journal of Environmental Science, 45(2), 38-52. https://doi.org/10.1234/jes.2023.01.001"
      ]
    },
    "machine learning medicine": {
      results: [
        {
          text: "Machine learning algorithms have demonstrated 94% accuracy in early diagnosis of certain cancers, exceeding traditional diagnostic methods by 15-20%.",
          source: "Brown, R., & Davis, S. (2023, S. 112)"
        },
        {
          text: "Challenges in implementing ML systems in clinical settings include data privacy concerns, integration with existing healthcare IT infrastructure, and the need for model transparency.",
          source: "Brown, R., & Davis, S. (2023, S. 115)"
        }
      ],
      bibliography: [
        "Brown, R., & Davis, S. (2023). Machine Learning Applications in Medicine. Medical Informatics Journal, 32(4), 105-120. https://doi.org/10.5678/mij.2023.02.005"
      ]
    }
  };
  
  // Unterstützte Zitationsstile
  const mockCitationStyles = [
    { id: "apa", name: "APA 7th Edition" },
    { id: "chicago", name: "Chicago 18th Edition" },
    { id: "harvard", name: "Harvard" },
  ];
  
  // Mock für das Speichern eines neuen Dokuments
  const saveDocument = (documentData, file = null) => {
    const newId = `doc${mockDocuments.length + 1}`;
    const newDocument = {
      id: newId,
      ...documentData.metadata,
      uploadDate: new Date().toISOString(),
      // Wir fügen nur die wichtigsten Felder hinzu, für Testzwecke reicht das
    };
    
    // Im echten System würden hier Chunks erstellt und in der Vektordatenbank gespeichert
    console.log("Mock: Document saved", newDocument);
    
    // In einem echten System würden wir das neue Dokument zum Array hinzufügen
    // Hier ist das nicht notwendig, da wir bei jedem Seitenaufruf die komplette Liste neu laden
    
    return newDocument;
  };
  
  // Mock für Suchanfragen
  const queryDocuments = (queryParams) => {
    const { query, citation_style = "apa" } = queryParams;
    
    // Vereinfachte Schlüsselwortsuche durch die Mock-Daten
    let results = [];
    let bibliography = [];
    
    // Einfache Keyword-Suche in unseren Beispieldaten
    for (const [key, value] of Object.entries(mockQueryResults)) {
      const keywords = key.split(" ");
      if (keywords.some(word => query.toLowerCase().includes(word.toLowerCase()))) {
        results = [...results, ...value.results];
        bibliography = [...bibliography, ...value.bibliography];
      }
    }
    
    // Wenn nichts gefunden wurde, generische Antwort
    if (results.length === 0) {
      results = [
        {
          text: "Zu dieser Anfrage wurden keine relevanten Informationen in den gespeicherten Dokumenten gefunden.",
          source: "System"
        }
      ];
    }
    
    return {
      results,
      bibliography: [...new Set(bibliography)], // Duplikate entfernen
      query,
      citation_style
    };
  };
  
  // Exportiere die Mock-Funktionen
  export default {
    documents: mockDocuments,
    citationStyles: mockCitationStyles,
    saveDocument,
    queryDocuments,
    isTestMode: true
  };