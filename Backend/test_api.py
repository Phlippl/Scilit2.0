#!/usr/bin/env python
# Backend/test_api.py
"""
Skript zum Testen der API-Endpunkte
"""
import requests
import json
import sys
import os
from pprint import pprint

# Basis-URL der API
API_URL = "http://localhost:5000/api"

def test_metadata_doi():
    """Test der DOI-Metadaten-API"""
    print("\n=== Test: DOI-Metadaten ===")
    doi = "10.1038/s41586-020-2649-2"  # Beispiel-DOI von Nature
    
    response = requests.get(f"{API_URL}/metadata/doi/{doi}")
    
    if response.status_code == 200:
        print(f"✅ DOI-Metadaten erfolgreich abgerufen: Status {response.status_code}")
        pprint(response.json())
    else:
        print(f"❌ Fehler beim Abrufen der DOI-Metadaten: Status {response.status_code}")
        print(response.text)

def test_metadata_isbn():
    """Test der ISBN-Metadaten-API"""
    print("\n=== Test: ISBN-Metadaten ===")
    isbn = "9780262539920"  # Beispiel-ISBN
    
    response = requests.get(f"{API_URL}/metadata/isbn/{isbn}")
    
    if response.status_code == 200:
        print(f"✅ ISBN-Metadaten erfolgreich abgerufen: Status {response.status_code}")
        pprint(response.json())
    else:
        print(f"❌ Fehler beim Abrufen der ISBN-Metadaten: Status {response.status_code}")
        print(response.text)

def test_citation_styles():
    """Test der Zitationsstil-API"""
    print("\n=== Test: Verfügbare Zitationsstile ===")
    
    response = requests.get(f"{API_URL}/query/citation-styles")
    
    if response.status_code == 200:
        print(f"✅ Zitationsstile erfolgreich abgerufen: Status {response.status_code}")
        pprint(response.json())
    else:
        print(f"❌ Fehler beim Abrufen der Zitationsstile: Status {response.status_code}")
        print(response.text)

def test_documents_list():
    """Test der Dokument-Auflistungs-API"""
    print("\n=== Test: Dokumente auflisten ===")
    
    response = requests.get(f"{API_URL}/documents")
    
    if response.status_code == 200:
        print(f"✅ Dokumente erfolgreich abgerufen: Status {response.status_code}")
        pprint(response.json())
    else:
        print(f"❌ Fehler beim Abrufen der Dokumente: Status {response.status_code}")
        print(response.text)

def test_query():
    """Test der Abfrage-API"""
    print("\n=== Test: Abfrage an Dokumente ===")
    
    query_data = {
        "query": "Wie beeinflusst der Klimawandel die Landwirtschaft?",
        "citation_style": "apa",
        "n_results": 3,
        "use_direct_quotes": True,
        "include_page_numbers": True
    }
    
    response = requests.post(f"{API_URL}/query", json=query_data)
    
    if response.status_code == 200:
        print(f"✅ Abfrage erfolgreich: Status {response.status_code}")
        print("\nErgebnisse:")
        for idx, result in enumerate(response.json().get('results', [])):
            print(f"\n[{idx+1}] {result.get('text')}")
            print(f"   Quelle: {result.get('source')}")
        
        print("\nBibliographie:")
        for item in response.json().get('bibliography', []):
            print(f"- {item}")
    else:
        print(f"❌ Fehler bei der Abfrage: Status {response.status_code}")
        print(response.text)

def main():
    """Hauptfunktion"""
    print("SciLit2.0 API-Test")
    print("=====================================")
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "doi":
            test_metadata_doi()
        elif test_name == "isbn":
            test_metadata_isbn()
        elif test_name == "styles":
            test_citation_styles()
        elif test_name == "documents":
            test_documents_list()
        elif test_name == "query":
            test_query()
        else:
            print(f"Unbekannter Test: {test_name}")
            print("Verfügbare Tests: doi, isbn, styles, documents, query")
    else:
        # Alle Tests ausführen
        test_metadata_doi()
        test_metadata_isbn()
        test_citation_styles()
        test_documents_list()
        test_query()

if __name__ == "__main__":
    main()