#!/usr/bin/env python3
# Backend/app.py
"""
Hauptanwendung für SciLit2.0 Backend
"""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Blueprints importieren
from api.documents import documents_bp
from api.metadata import metadata_bp
from api.query import query_bp

# Gemeinsam genutzte Komponenten importieren
import spacy
from pathlib import Path

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scilit.log')
    ]
)

logger = logging.getLogger(__name__)

# Umgebungsvariablen laden
load_dotenv()

# Konfigurationswerte
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './uploads')
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 20 * 1024 * 1024))
CHROMA_PERSIST_DIR = os.environ.get('CHROMA_PERSIST_DIR', './data/chroma')
ALLOWED_EXTENSIONS = {'pdf'}

# spaCy-Modell initialisieren
def initialize_nlp():
    """SpaCy-Modell initialisieren"""
    try:
        nlp = spacy.load("en_core_web_sm")
        logger.info("Loaded spaCy model: en_core_web_sm")
        return nlp
    except OSError:
        try:
            nlp = spacy.load("de_core_news_sm")
            logger.info("Loaded spaCy model: de_core_news_sm")
            return nlp
        except OSError:
            logger.warning("No spaCy model found. Downloading en_core_web_sm...")
            try:
                spacy.cli.download("en_core_web_sm")
                nlp = spacy.load("en_core_web_sm")
                logger.info("Downloaded and loaded spaCy model: en_core_web_sm")
                return nlp
            except Exception as e:
                logger.error(f"Failed to download spaCy model: {e}")
                nlp = spacy.blank("en")
                logger.warning("Using blank spaCy model")
                return nlp

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Konfiguration laden
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['CHROMA_PERSIST_DIR'] = CHROMA_PERSIST_DIR
    app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
    
    # SpaCy-Modell initialisieren und als Anwendungsvariable verfügbar machen
    app.config['NLP_MODEL'] = initialize_nlp()
    
    # CORS aktivieren
    CORS(app)
    
    # Blueprints registrieren
    app.register_blueprint(documents_bp)
    app.register_blueprint(metadata_bp)
    app.register_blueprint(query_bp)
    
    # Verzeichnisse sicherstellen
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    
    # Root-Route für Gesundheitscheck
    @app.route('/')
    def health_check():
        return jsonify({
            'status': 'ok', 
            'version': '1.0.0',
            'app': 'SciLit2.0 API'
        })
    
    # Fehlerbehandlungsrouten
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404
    
    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": f"File too large. Maximum size: {MAX_CONTENT_LENGTH/(1024*1024)}MB"}), 413
    
    return app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('DEBUG', 'True').lower() == 'true')