# Backend/services/authentication/__init__.py
"""
Zentrales Authentication Package für SciLit2.0
"""

from .auth_manager import AuthManager
from .storage import JSONAuthStorage, SQLAuthStorage

# Singleton-Instanz für einfachen Zugriff
def get_auth_manager():
    """Gibt die aktuelle AuthManager-Instanz zurück"""
    from flask import current_app
    
    if hasattr(current_app, 'auth_manager'):
        return current_app.auth_manager
    
    # Fallback wenn keine App-Kontext verfügbar ist
    from .auth_manager import _default_auth_manager
    return _default_auth_manager