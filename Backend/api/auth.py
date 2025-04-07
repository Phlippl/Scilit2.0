from flask import Blueprint, jsonify, request, current_app
import logging
import jwt
import datetime
from services.user_service import UserService

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Instanz des UserService erstellen
user_service = UserService()

@auth_bp.route('/register', methods=['POST'])
def register():
    """Benutzer registrieren"""
    if not request.is_json:
        return jsonify({"error": "Anfrage muss JSON sein"}), 400
    
    data = request.get_json()
    
    # Pflichtfelder prüfen
    required_fields = ['email', 'password', 'name']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Feld '{field}' ist erforderlich"}), 400
    
    # Benutzer erstellen
    user, error = user_service.create_user(
        email=data['email'],
        password=data['password'],
        name=data['name']
    )
    
    if error:
        return jsonify({"error": error}), 400
    
    # JWT-Token erstellen
    secret_key = current_app.config['SECRET_KEY']
    token = jwt.encode({
        'sub': user['id'],
        'email': user['email'],
        'name': user['name'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }, secret_key, algorithm='HS256')
    
    return jsonify({
        "user": user,
        "token": token
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Benutzer anmelden"""
    if not request.is_json:
        return jsonify({"error": "Anfrage muss JSON sein"}), 400
    
    data = request.get_json()
    
    # Pflichtfelder prüfen
    if 'email' not in data or 'password' not in data:
        return jsonify({"error": "E-Mail und Passwort sind erforderlich"}), 400
    
    # Benutzer authentifizieren
    user, error = user_service.authenticate_user(
        email=data['email'],
        password=data['password']
    )
    
    if error:
        return jsonify({"error": error}), 401
    
    # JWT-Token erstellen
    secret_key = current_app.config['SECRET_KEY']
    token = jwt.encode({
        'sub': user['id'],
        'email': user['email'],
        'name': user['name'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }, secret_key, algorithm='HS256')
    
    return jsonify({
        "user": user,
        "token": token
    })

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Aktuell angemeldeten Benutzer abrufen"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authentifizierung erforderlich"}), 401
    
    token = auth_header.split(' ')[1]
    
    try:
        # Token decodieren
        secret_key = current_app.config['SECRET_KEY']
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        
        # Benutzer abrufen
        user = user_service.get_user_by_email(payload['email'])
        
        if not user:
            return jsonify({"error": "Benutzer nicht gefunden"}), 404
        
        return jsonify(user)
        
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token abgelaufen"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Ungültiger Token"}), 401
    
@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Benutzer abmelden (Client löscht den Token)"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authentifizierung erforderlich"}), 401

    # In diesem einfachen Ansatz wird keine serverseitige Aktion ausgeführt.
    # Der Client sollte den Token nach erfolgreicher Abmeldung löschen.
    return jsonify({"message": "Erfolgreich ausgeloggt. Bitte Token auf Clientseite entfernen."}), 200
