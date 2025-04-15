#!/usr/bin/env python3
# Backend/app.py

import os
import logging
import time
import threading
import concurrent.futures
import secrets
import spacy
import sys
from flask import Flask, jsonify, g, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv

# Import blueprints
from api.documents import documents_bp, get_executor
from api.metadata import metadata_bp
from api.query import query_bp
from api.auth import auth_bp

# Prevent .pyc files
sys.dont_write_bytecode = True

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scilit.log')
    ]
)
logger = logging.getLogger(__name__)

# Load .env
load_dotenv()

# Environment config
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './uploads')
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 20 * 1024 * 1024))
CHROMA_PERSIST_DIR = os.environ.get('CHROMA_PERSIST_DIR', './data/chroma')
ALLOWED_EXTENSIONS = {'pdf'}

# Executor for background tasks
background_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def initialize_nlp():
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
            logger.warning("Downloading en_core_web_sm...")
            try:
                spacy.cli.download("en_core_web_sm")
                return spacy.load("en_core_web_sm")
            except Exception as e:
                logger.error(f"spaCy download failed: {e}")
                return spacy.blank("en")

def check_embeddings():
    try:
        import requests
        url = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434')
        res = requests.get(f"{url}/api/version", timeout=5)
        if res.status_code == 200:
            logger.info(f"Connected to Ollama API: {res.json()}")
        else:
            logger.warning(f"Unexpected Ollama response: {res.status_code}")
    except Exception as e:
        logger.warning(f"Ollama check failed: {e}")

def init_directories():
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        os.makedirs(os.path.join(UPLOAD_FOLDER, 'status'), exist_ok=True)
        logger.info(f"Upload folder ready: {UPLOAD_FOLDER}")
        logger.info(f"ChromaDB folder ready: {CHROMA_PERSIST_DIR}")
    except Exception as e:
        logger.error(f"Directory init failed: {e}")

def create_app():
    init_directories()
    app = Flask(__name__)

    # Proper CORS
    CORS(app, origins=["http://localhost:5173"], supports_credentials=True)

    # App config
    app.config.update({
        'UPLOAD_FOLDER': UPLOAD_FOLDER,
        'MAX_CONTENT_LENGTH': MAX_CONTENT_LENGTH,
        'CHROMA_PERSIST_DIR': CHROMA_PERSIST_DIR,
        'ALLOWED_EXTENSIONS': ALLOWED_EXTENSIONS,
        'SECRET_KEY': os.environ.get('SECRET_KEY', secrets.token_hex(32)),
        'NLP_MODEL': initialize_nlp()
    })

    # Register blueprints
    app.register_blueprint(documents_bp)
    app.register_blueprint(metadata_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(auth_bp)

    # Services
    background_executor.submit(check_embeddings)

    # Optional test user
    from services.auth_service import AuthService
    auth = AuthService()
    email = os.environ.get('VITE_TEST_USER_EMAIL', 'user@example.com')
    if not auth.get_user_by_email(email):
        auth.create_user(
            email=email,
            password=os.environ.get('VITE_TEST_USER_PASSWORD', 'password123'),
            name=os.environ.get('VITE_TEST_USER_NAME', 'Test User')
        )

    # Routes
    @app.route('/')
    def health():
        return jsonify({'status': 'ok', 'version': '1.1.0', 'app': 'SciLit2.0 API'})

    @app.route('/stream-test')
    def stream():
        def generate():
            for i in range(10):
                yield f"data: {i}\n\n"
                time.sleep(0.5)
        return Response(stream_with_context(generate()), content_type='text/event-stream')

    # Error handlers
    @app.errorhandler(404)
    def not_found(e): return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(413)
    def too_large(e): return jsonify({"error": f"File too large. Max: {MAX_CONTENT_LENGTH / (1024 * 1024)}MB"}), 413

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({"error": "Internal server error"}), 500

    @app.before_request
    def before():
        g.start_time = time.time()

    @app.after_request
    def after(response):
        if hasattr(g, 'start_time'):
            logger.info(f"Request took {time.time() - g.start_time:.4f}s")
        return response

    @app.teardown_appcontext
    def shutdown(_):
        try:
            logger.info("Shutting down executors...")
            try:
                executor = get_executor()
                if executor and hasattr(executor, 'shutdown'):
                    executor.shutdown(wait=False)
                    logger.info("Main executor shut down")
            except Exception as e:
                logger.warning(f"Executor shutdown failed: {e}")

            if background_executor:
                background_executor.shutdown(wait=False)
                logger.info("Background executor shut down")
        except Exception as e:
            logger.error(f"Global teardown failed: {e}")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=os.environ.get('HOST', '0.0.0.0'),
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('DEBUG', 'True').lower() == 'true'
    )
