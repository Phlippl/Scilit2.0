# Backend/api/query.py
import os
import json
import logging
import re
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
import requests

# Eigene Services importieren
from services.vector_db import search_documents
from services.citation_service import format_citation

logger = logging.getLogger(__name__)

# Blueprint für Query-API erstellen
query_bp = Blueprint('query', __name__, url_prefix='/api/query')

# Konfiguration für LLM-Integration
LLM_API_URL = os.environ.get('LLM_API_URL', 'https://api.openai.com/v1/chat/completions')
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-3.5-turbo')

# Unterstützte Zitationsstile
CITATION_STYLES = [
    {"id": "apa", "name": "APA 7th Edition"},
    {"id": "chicago", "name": "Chicago 18th Edition"},
    {"id": "harvard", "name": "Harvard"}
]


@query_bp.route('', methods=['POST'])
def query_documents_api():
    """
    Abfrage an die Dokumente stellen und LLM für Antworten verwenden
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        # Erforderliche Parameter prüfen
        if 'query' not in data or not data['query'].strip():
            return jsonify({"error": "Query text is required"}), 400
        
        # Parameter extrahieren
        query_text = data['query'].strip()
        citation_style = data.get('citation_style', 'apa')
        document_ids = data.get('document_ids', None)
        n_results = int(data.get('n_results', 5))
        use_direct_quotes = data.get('use_direct_quotes', True)
        include_page_numbers = data.get('include_page_numbers', True)
        
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # Filter für Dokumente
        filters = {}
        if document_ids:
            filters['document_ids'] = document_ids
        
        # Relevante Dokumente suchen
        search_results = search_documents(
            query=query_text,
            user_id=user_id,
            filters=filters,
            n_results=n_results * 2,  # Mehr Ergebnisse abrufen für besseren LLM-Kontext
            include_metadata=True
        )
        
        if not search_results or len(search_results) == 0:
            return jsonify({
                "results": [],
                "bibliography": [],
                "query": query_text
            })
        
        # LLM-Antwort generieren
        llm_response = generate_llm_response(
            query_text=query_text,
            search_results=search_results,
            citation_style=citation_style,
            use_direct_quotes=use_direct_quotes,
            include_page_numbers=include_page_numbers
        )
        
        # Antwort zurückgeben
        return jsonify(llm_response)
    
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        return jsonify({"error": f"Failed to query documents: {str(e)}"}), 500


def generate_llm_response(query_text, search_results, citation_style='apa', use_direct_quotes=True, include_page_numbers=True):
    """
    LLM für Antwortgenerierung verwenden
    
    Args:
        query_text: Abfragetext
        search_results: Suchergebnisse aus der Vektordatenbank
        citation_style: Zitationsstil
        use_direct_quotes: Direkte Zitate verwenden
        include_page_numbers: Seitenzahlen einbeziehen
    
    Returns:
        dict: LLM-Antwort mit Ergebnissen und Bibliographie
    """
    try:
        # Wenn kein API-Key oder URL, simulierte Antwort zurückgeben
        if not LLM_API_KEY or LLM_API_URL == '':
            logger.warning("No LLM API configuration, using simulated response")
            return simulate_llm_response(search_results, citation_style)
        
        # Kontext für das LLM vorbereiten
        context = []
        documents_for_bibliography = {}
        
        for result in search_results:
            context.append(f"CONTENT: {result['text']}")
            
            # Quelle für Bibliographie merken
            if 'metadata' in result and 'document_id' in result['metadata']:
                doc_id = result['metadata']['document_id']
                if doc_id not in documents_for_bibliography:
                    documents_for_bibliography[doc_id] = {
                        "title": result['metadata'].get('title', ''),
                        "authors": result['metadata'].get('authors', '[]'),
                        "publication_date": result['metadata'].get('publication_date', ''),
                        "journal": result['metadata'].get('journal', ''),
                        "publisher": result['metadata'].get('publisher', ''),
                        "doi": result['metadata'].get('doi', ''),
                        "isbn": result['metadata'].get('isbn', ''),
                        "type": result['metadata'].get('type', 'other')
                    }
                    
                    # JSON-String zu Liste parsen, falls nötig
                    if isinstance(documents_for_bibliography[doc_id]['authors'], str):
                        try:
                            documents_for_bibliography[doc_id]['authors'] = json.loads(documents_for_bibliography[doc_id]['authors'])
                        except:
                            documents_for_bibliography[doc_id]['authors'] = []
        
        # Anweisungen für das LLM
        system_prompt = f"""
        Als wissenschaftlicher Assistent sollst du Fragen basierend auf den bereitgestellten Dokumenten beantworten.
        
        Berücksichtige bei deiner Antwort folgende Regeln:
        1. Verwende NUR die Informationen aus den bereitgestellten Dokumenten.
        2. Wenn die Dokumente keine ausreichenden Informationen zur Beantwortung der Frage enthalten, sage das offen.
        3. Zitationsstil: {citation_style.upper()}
        4. {'' if use_direct_quotes else 'Vermeide direkte Zitate. Paraphrasiere stattdessen die Informationen.'}
        5. {'' if include_page_numbers else 'Lasse Seitenzahlen in den Zitaten weg.'}
        6. Gib für jede wichtige Information ein Kurzzitat im Format (Autor, Jahr{', S. XX' if include_page_numbers else ''}) an.
        7. Formatiere deine Antwort als Liste von Abschnitten, wobei jeder Abschnitt aus dem Text und der dazugehörigen Quellenangabe besteht.
        8. Die Antwort sollte objektiv und informativ sein.
        """
        
        # Prompt für das LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Frage: {query_text}\n\nDokumentabschnitte:\n" + "\n\n".join(context)}
        ]
        
        # LLM-Anfrage
        response = requests.post(
            LLM_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LLM_API_KEY}"
            },
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 0.3,  # Niedrige Temperatur für präzisere Antworten
                "max_tokens": 1000
            }
        )
        
        if response.status_code != 200:
            logger.error(f"LLM API error: {response.text}")
            raise Exception(f"LLM API error: {response.status_code}")
        
        llm_data = response.json()
        llm_text = llm_data['choices'][0]['message']['content']
        
        # LLM-Antwort in Teile aufteilen und strukturieren
        results = []
        # Einfache Parsing-Logik - in einer echten Implementierung wäre dies robuster
        sections = llm_text.split('\n\n')
        for section in sections:
            if not section.strip():
                continue
                
            # Quelle extrahieren (falls vorhanden)
            source_match = re.search(r'\(([^)]+)\)$', section)
            if source_match:
                text_part = section[:source_match.start()].strip()
                source_part = source_match.group(1)
                results.append({"text": text_part, "source": source_part})
            else:
                results.append({"text": section, "source": ""})
        
        # Bibliographie generieren
        bibliography = []
        for doc_id, doc_info in documents_for_bibliography.items():
            # Zitation im gewählten Stil formatieren
            citation = format_citation(
                doc_info,
                style=citation_style
            )
            if citation and citation not in bibliography:
                bibliography.append(citation)
        
        return {
            "results": results,
            "bibliography": bibliography,
            "query": query_text
        }
            
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return simulate_llm_response(search_results, citation_style)


def simulate_llm_response(search_results, citation_style):
    """
    Simuliert eine LLM-Antwort wenn keine LLM-API verfügbar ist
    
    Args:
        search_results: Suchergebnisse
        citation_style: Zitationsstil
    
    Returns:
        dict: Simulierte Antwort
    """
    results = []
    bibliography = []
    documents_for_bibliography = {}
    
    # Direkt die Suchergebnisse als Antworten verwenden
    for result in search_results:
        result_item = {
            "text": result["text"],
            "source": result.get("source", "")
        }
        results.append(result_item)
        
        # Dokumente für Bibliographie sammeln
        if 'metadata' in result and 'document_id' in result['metadata']:
            doc_id = result['metadata']['document_id']
            if doc_id not in documents_for_bibliography:
                documents_for_bibliography[doc_id] = {
                    "title": result['metadata'].get('title', ''),
                    "authors": result['metadata'].get('authors', '[]'),
                    "publication_date": result['metadata'].get('publication_date', ''),
                    "journal": result['metadata'].get('journal', ''),
                    "publisher": result['metadata'].get('publisher', ''),
                    "doi": result['metadata'].get('doi', ''),
                    "isbn": result['metadata'].get('isbn', ''),
                    "type": result['metadata'].get('type', 'other')
                }
                
                # JSON-String zu Liste parsen, falls nötig
                if isinstance(documents_for_bibliography[doc_id]['authors'], str):
                    try:
                        documents_for_bibliography[doc_id]['authors'] = json.loads(documents_for_bibliography[doc_id]['authors'])
                    except:
                        documents_for_bibliography[doc_id]['authors'] = []
    
    # Bibliographie generieren
    for doc_id, doc_info in documents_for_bibliography.items():
        citation = format_citation(doc_info, style=citation_style)
        if citation:
            bibliography.append(citation)
    
    return {
        "results": results[:5],  # Beschränkung auf 5 Ergebnisse
        "bibliography": bibliography,
        "query": "Simulierte Antwort (kein LLM verfügbar)"
    }


@query_bp.route('/citation-styles', methods=['GET'])
def get_citation_styles():
    """
    Verfügbare Zitationsstile abrufen
    """
    return jsonify(CITATION_STYLES)


@query_bp.route('/save', methods=['POST'])
def save_query():
    """
    Abfrage und Ergebnisse speichern
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # TODO: Abfrage in Datenbank speichern
        # In einer echten Implementierung würde die Abfrage hier gespeichert werden
        
        # Erfolg melden
        return jsonify({
            "id": "query_" + str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "saved": True
        })
    
    except Exception as e:
        logger.error(f"Error saving query: {e}")
        return jsonify({"error": f"Failed to save query: {str(e)}"}), 500


@query_bp.route('/saved', methods=['GET'])
def get_saved_queries():
    """
    Gespeicherte Abfragen abrufen
    """
    try:
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # TODO: Abfragen aus Datenbank laden
        # In einer echten Implementierung würden die Abfragen hier geladen werden
        
        # Leere Liste zurückgeben
        return jsonify([])
    
    except Exception as e:
        logger.error(f"Error retrieving saved queries: {e}")
        return jsonify({"error": f"Failed to retrieve saved queries: {str(e)}"}), 500