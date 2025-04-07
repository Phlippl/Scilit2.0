#!/usr/bin/env python3
# Backend/app.py
"""
Main application for SciLit2.0 Backend with improved initialization and error handling
"""
import os
import logging
import time
import threading
from flask import Flask, jsonify, g, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
import concurrent.futures

from utils.resource_monitor import resource_monitor
import sys
sys.dont_write_bytecode = True  # Prevents Python from creating .pyc files

# Import Blueprints
from api.documents import documents_bp
from api.metadata import metadata_bp
from api.query import query_bp

# Import shared components
import spacy
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scilit.log')
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration values
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './uploads')
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 20 * 1024 * 1024))
CHROMA_PERSIST_DIR = os.environ.get('CHROMA_PERSIST_DIR', './data/chroma')
ALLOWED_EXTENSIONS = {'pdf'}

# Thread pool for background tasks
background_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

# Initialize spaCy model
def initialize_nlp():
    """Initialize spaCy model with proper fallbacks"""
    try:
        nlp = spacy.load("de_core_news_sm")
        logger.info("Loaded spaCy model: de_core_news_sm")
        return nlp
    except OSError:
        try:
            nlp = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model: en_core_web_sm")
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

def check_embeddings():
    """Check if vector embeddings service is available and log status"""
    try:
        from services.vector_db import client as vector_client
        from services.ollama_embeddings import OllamaEmbeddingFunction
        
        # Check if Ollama server is running 
        ollama_url = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434')
        import requests
        response = requests.get(f"{ollama_url}/api/version", timeout=5)
        
        if response.status_code == 200:
            logger.info(f"Connected to Ollama API: {response.json()}")
        else:
            logger.warning(f"Ollama API returned unexpected status: {response.status_code}")
    except Exception as e:
        logger.warning(f"Embeddings service check failed: {e}")
        logger.warning("Will use fallback embedding function - performance may be reduced")

def init_directories():
    """Ensure all required directories exist"""
    try:
        # Create upload folder
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        logger.info(f"Upload folder ready: {UPLOAD_FOLDER}")
        
        # Create ChromaDB directory
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        logger.info(f"ChromaDB directory ready: {CHROMA_PERSIST_DIR}")
        
        # Create any other required directories
        log_dir = os.path.dirname('scilit.log')
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating directories: {e}")
        raise

def create_app():
    """Create and configure the Flask application."""
    # Initialize directories first
    init_directories()
    
    app = Flask(__name__)
    
    # Load configuration
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['CHROMA_PERSIST_DIR'] = CHROMA_PERSIST_DIR
    app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
    
    # Initialize spaCy model and make available as application variable
    app.config['NLP_MODEL'] = initialize_nlp()
    
    # Enable CORS
    CORS(app)
    
    # Register Blueprints
    app.register_blueprint(documents_bp)
    app.register_blueprint(metadata_bp)
    app.register_blueprint(query_bp)
    
    # Start background services check
    background_executor.submit(check_embeddings)
    
    # Root route for health check
    @app.route('/')
    def health_check():
        return jsonify({
            'status': 'ok', 
            'version': '1.1.0',
            'app': 'SciLit2.0 API'
        })
    
    # Add streaming support endpoint
    @app.route('/stream-test')
    def stream_test():
        def generate():
            for i in range(10):
                yield f"data: {i}\n\n"
                time.sleep(0.5)
        return Response(stream_with_context(generate()), content_type='text/event-stream')
    
    # Error handling routes
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
    
    # Request handling hooks
    @app.before_request
    def before_request():
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            logger.info(f"Request processed in {elapsed:.4f}s")
        return response
    
    resource_monitor.start()

    # Shutdown hook to clean up resources
    @app.teardown_appcontext
    def teardown_resources(exception):
        # Proper executor shutdown with timeout
        from api.documents import executor
        executor.shutdown(wait=True, cancel_futures=True)  # Für Python 3.9+
        # Für ältere Python-Versionen:
        # futures = list(executor._work_queue.queue)
        # for future in futures:
        #     future.cancel()
        # executor.shutdown(wait=True)
        
        # Clean up other resources if needed
        logger.info("Application shutting down, resources cleaned up")
    
    return app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    app = create_app()
    app.run(host=host, port=port, debug=debug)