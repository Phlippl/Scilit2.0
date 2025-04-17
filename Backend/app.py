# Backend/app.py
"""
Hauptanwendung für das SciLit2.0-Backend mit verbesserter Initialisierung
und sauberer Auftrennungen der Verantwortlichkeiten.
"""
import logging
import time
import concurrent.futures
import sys
from flask import Flask, jsonify, g, Response, stream_with_context, request, current_app
from flask_cors import CORS

# Zentralisierte Konfiguration und Services
from config import config_manager
from services.registry import initialize_services, get
from services.status_service import initialize_status_service
from utils.error_handler import configure_error_handlers, APIError

# Verhindere .pyc-Dateien
sys.dont_write_bytecode = True

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scilit.log')
    ]
)
logger = logging.getLogger(__name__)

# Executor für Hintergrundaufgaben
background_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def initialize_nlp():
    """Initialisiert und gibt das spaCy NLP-Modell zurück"""
    try:
        import spacy
        try:
            nlp = spacy.load("de_core_news_sm")
            logger.info("spaCy-Modell geladen: de_core_news_sm")
            return nlp
        except OSError:
            try:
                nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy-Modell geladen: en_core_web_sm")
                return nlp
            except OSError:
                logger.warning("Lade en_core_web_sm herunter...")
                try:
                    spacy.cli.download("en_core_web_sm")
                    return spacy.load("en_core_web_sm")
                except Exception as e:
                    logger.error(f"spaCy-Download fehlgeschlagen: {e}")
                    return spacy.blank("en")
    except ImportError:
        logger.warning("spaCy nicht verfügbar, verwende leeres Modell")
        return None

def check_embeddings():
    """Prüft, ob Ollama-Embeddings-Service verfügbar ist"""
    try:
        import requests
        url = config_manager.get('OLLAMA_API_URL', 'http://localhost:11434')
        res = requests.get(f"{url}/api/version", timeout=5)
        if res.status_code == 200:
            logger.info(f"Verbindung zur Ollama-API hergestellt: {res.json()}")
        else:
            logger.warning(f"Unerwartete Ollama-Antwort: {res.status_code}")
    except Exception as e:
        logger.warning(f"Ollama-Prüfung fehlgeschlagen: {e}")

def init_directories():
    """Initialisiert benötigte Verzeichnisse"""
    try:
        import os
        
        upload_folder = config_manager.get('UPLOAD_FOLDER', './uploads')
        chroma_persist_dir = config_manager.get('CHROMA_PERSIST_DIR', './data/chroma')
        
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(chroma_persist_dir, exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'status'), exist_ok=True)
        
        logger.info(f"Upload-Verzeichnis bereit: {upload_folder}")
        logger.info(f"ChromaDB-Verzeichnis bereit: {chroma_persist_dir}")
    except Exception as e:
        logger.error(f"Verzeichnisinitialisierung fehlgeschlagen: {e}")

def create_test_user(auth_manager):
    """Erstellt einen Testbenutzer"""
    email = config_manager.get('TEST_USER_EMAIL', 'user@example.com')
    if not auth_manager.get_user_by_email(email):
        auth_manager.create_user(
            email=email,
            password=config_manager.get('TEST_USER_PASSWORD', 'password123'),
            name=config_manager.get('TEST_USER_NAME', 'Test User')
        )
        logger.info(f"Testbenutzer erstellt: {email}")

def create_app():
    """Erstellt und konfiguriert die Flask-Anwendung"""
    # Initialisiere Verzeichnisse
    init_directories()
    
    # Erstelle Flask-App
    app = Flask(__name__)

    # Konfiguriere CORS
    CORS(app, 
         origins=["http://localhost:5173", "http://localhost:5000", "http://localhost:3000"], 
         supports_credentials=True)

    # App-Konfiguration
    app.config.update({
        'UPLOAD_FOLDER': config_manager.get('UPLOAD_FOLDER', './uploads'),
        'MAX_CONTENT_LENGTH': config_manager.get('MAX_CONTENT_LENGTH', 20 * 1024 * 1024),
        'CHROMA_PERSIST_DIR': config_manager.get('CHROMA_PERSIST_DIR', './data/chroma'),
        'ALLOWED_EXTENSIONS': config_manager.get('ALLOWED_EXTENSIONS', {'pdf'}),
        'SECRET_KEY': config_manager.get('SECRET_KEY'),
        'NLP_MODEL': initialize_nlp()
    })

    # Fehlerbehandlung registrieren
    configure_error_handlers(app)

    # Blueprints importieren (verzögert)
    from api.documents.routes import documents_bp
    from api.metadata import metadata_bp
    from api.query import query_bp
    from api.auth import auth_bp
    
    # Blueprints registrieren
    app.register_blueprint(documents_bp)
    app.register_blueprint(metadata_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(auth_bp)

    # Services initialisieren
    initialize_services()

    # Mit App-Kontext aufrufen
    with app.app_context():
        # Status-Service initialisieren
        initialize_status_service()

        # Auth-Manager holen und im Kontext speichern
        from services.registry import get
        auth_manager = get('auth')
        current_app.auth_manager = auth_manager

        # Testbenutzer erstellen
        create_test_user(auth_manager)

    # Hintergrundprüfung für Embeddings starten
    background_executor.submit(check_embeddings)

    # Health Check
    @app.route('/')
    def health():
        return jsonify({
            'status': 'ok', 
            'version': '1.1.0', 
            'app': 'SciLit2.0 API',
            'time': time.strftime('%Y-%m-%d %H:%M:%S')
        })

    # Teststream-Route
    @app.route('/stream-test')
    def stream():
        def generate():
            for i in range(10):
                yield f"data: {i}\n\n"
                time.sleep(0.5)
        return Response(stream_with_context(generate()), content_type='text/event-stream')

    # Timing & Logging
    @app.before_request
    def before():
        g.start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID') or str(time.time())

    @app.after_request
    def after(response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            logger.info(f"Anfrage dauerte {duration:.4f}s")
            response.headers['X-Processing-Time'] = f"{duration:.4f}s"
            if hasattr(g, 'request_id'):
                response.headers['X-Request-ID'] = g.request_id
        return response

    # Shutdown
    @app.teardown_appcontext
    def shutdown(_):
        """Bereinigt Ressourcen beim Herunterfahren"""
        try:
            logger.info("Fahre Executors herunter...")

            # Document-Executor
            try:
                from api.documents.controller import get_executor
                executor = get_executor()
                if executor and hasattr(executor, 'shutdown'):
                    executor.shutdown(wait=False)
                    logger.info("Haupt-Executor heruntergefahren")
            except Exception as e:
                logger.warning(f"Executor-Shutdown fehlgeschlagen: {e}")

            # Hintergrund-Executor
            if background_executor:
                background_executor.shutdown(wait=False)
                logger.info("Hintergrund-Executor heruntergefahren")
                
        except Exception as e:
            logger.error(f"Globaler Teardown fehlgeschlagen: {e}")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=config_manager.get('HOST', '0.0.0.0'),
        port=config_manager.get('PORT', 5000),
        debug=config_manager.get('DEBUG', True)
    )