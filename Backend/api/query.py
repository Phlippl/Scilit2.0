# Backend/api/query.py
"""
Blueprint für Query-API-Endpunkte
"""
import os
import json
import logging
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
import requests
import re

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
        
        # Ergebnisse mit Zitationsstil und Seitenzahlen formatieren
        formatted_results = []
        bibliography_entries = []
        documents_for_bibliography = {}
        
        for result in search_results:
            # Metadaten extrahieren
            metadata = result.get('metadata', {})
            document_id = metadata.get('document_id')
            
            # Zitat für dieses Ergebnis erstellen
            formatted_results.append({
                "text": result.get('text', ''),
                "source": result.get('source', ''),
                "metadata": metadata,
                "document_id": document_id
            })
            
            # Für jeden eindeutigen Dokumenten-Typ eine vollständige Zitation erstellen
            if document_id not in documents_for_bibliography:
                documents_for_bibliography[document_id] = metadata
        
        # Bibliographie erstellen
        for doc_metadata in documents_for_bibliography.values():
            citation = format_citation(doc_metadata, citation_style)
            if citation and citation not in bibliography_entries:
                bibliography_entries.append(citation)
        
        # LLM-Antwort generieren, falls konfiguriert
        if LLM_API_KEY:
            llm_response = generate_llm_response(
                query_text=query_text,
                search_results=formatted_results,
                citation_style=citation_style,
                use_direct_quotes=use_direct_quotes,
                include_page_numbers=include_page_numbers
            )
            
            # Wenn die LLM-Antwort erfolgreich war, verwende diese
            if llm_response:
                return jsonify({
                    "results": llm_response,
                    "bibliography": bibliography_entries,
                    "query": query_text
                })
        
        # Antwort ohne LLM oder als Fallback zurückgeben
        # Begrenzt auf die angeforderte Anzahl von Ergebnissen
        return jsonify({
            "results": formatted_results[:n_results],
            "bibliography": bibliography_entries,
            "query": query_text
        })
    
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
        list: LLM-Antwort mit Ergebnissen und Quellenangaben
    """
    try:
        # Wenn kein API-Key oder URL, simulierte Antwort zurückgeben
        if not LLM_API_KEY or LLM_API_URL == '':
            logger.warning("No LLM API configuration, using search results directly")
            return search_results
        
        # Kontext für das LLM vorbereiten
        context_items = []
        
        for i, result in enumerate(search_results):
            context_items.append(f"Information #{i+1}: {result['text']}")
            context_items.append(f"Citation #{i+1}: {result['source']}")
        
        context = "\n".join(context_items)
        
        # Anweisungen für Zitationsstil und Direktzitate
        citation_instructions = f"Use {citation_style.upper()} citation style."
        if not use_direct_quotes:
            citation_instructions += " Avoid direct quotes, paraphrase the information instead."
        if include_page_numbers:
            citation_instructions += " Include page numbers in citations when available."
        
        # Systemanweisung für das LLM
        system_prompt = f"""
        You are an academic assistant that helps researchers with literature queries.
        Answer the question based ONLY on the provided information.
        For each piece of information you use, include the citation in the format provided.
        {citation_instructions}
        Do not make up or infer information that is not explicitly stated in the provided context.
        Format your answer as a coherent paragraph or structured response.
        """
        
        # Benutzerprompt mit Kontext
        user_prompt = f"""
        Question: {query_text}
        
        Use ONLY the following information to answer the question:
        
        {context}
        """
        
        # LLM-Anfrage senden
        response = requests.post(
            LLM_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LLM_API_KEY}"
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,  # Niedrige Temperatur für präzisere Antworten
                "max_tokens": 1000
            },
            timeout=30  # 30 Sekunden Timeout
        )
        
        # Antwort verarbeiten
        if response.status_code == 200:
            llm_data = response.json()
            llm_text = llm_data['choices'][0]['message']['content']
            
            # LLM-Antwort in Absätze aufteilen
            paragraphs = re.split(r'\n\s*\n', llm_text)
            
            # Strukturierte Ergebnisse erstellen
            structured_results = []
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                
                # Nach Zitaten suchen (Muster: Text (Autor, Jahr, S. X))
                citation_matches = list(re.finditer(r'\((?:[^()]+,\s*)?[^()]+(?:,\s*S\.\s*\d+)?\)', paragraph))
                
                if citation_matches:
                    # Text und Zitat trennen
                    last_match = citation_matches[-1]
                    text = paragraph[:last_match.start()].strip()
                    source = last_match.group(0)
                    
                    structured_results.append({
                        "text": text,
                        "source": source
                    })
                else:
                    # Falls kein Zitat gefunden wurde, den ganzen Absatz verwenden
                    structured_results.append({
                        "text": paragraph,
                        "source": ""
                    })
            
            return structured_results
        else:
            logger.error(f"LLM API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return None


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