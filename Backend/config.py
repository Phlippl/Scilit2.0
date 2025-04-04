import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Base configuration class"""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.environ.get('DEBUG', 'True') == 'True'
    
    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret')
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Database settings
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/scilit')
    
    # Vector database settings
    CHROMA_PERSIST_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chroma_db')
    
    # CrossRef API settings
    CROSSREF_EMAIL = os.environ.get('CROSSREF_EMAIL', 'user@example.com')
    
    # LLM settings
    LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-3.5-turbo')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    
    # SpaCy model
    SPACY_MODEL = os.environ.get('SPACY_MODEL', 'en_core_web_md')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # Use stronger secret keys in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    
    # Require HTTPS in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Use a test database
    MONGO_URI = os.environ.get('TEST_MONGO_URI', 'mongodb://localhost:27017/scilit_test')
    
    # Use a test ChromaDB directory
    CHROMA_PERSIST_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_chroma_db')
