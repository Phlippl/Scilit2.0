# Backend/api/auth.py
from flask import Blueprint, jsonify, request, current_app
import logging
import jwt
import datetime
from services.authentication import get_auth_manager
from utils.auth_middleware import (
    get_token_from_header,
    verify_token,
    verify_token_with_options,
    get_current_user as middleware_get_current_user
)
from config import config_manager

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    # Check required fields
    required_fields = ['email', 'password', 'name']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Field '{field}' is required"}), 400
    
    # Get auth manager
    auth_manager = get_auth_manager()
    
    # Create user
    user, error = auth_manager.create_user(
        email=data['email'],
        password=data['password'],
        name=data['name']
    )
    
    if error:
        return jsonify({"error": error}), 400
    
    # Create JWT token
    secret_key = config_manager.get('SECRET_KEY')
    token = jwt.encode({
        'sub': user.id,
        'email': user.email,
        'name': user.name,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }, secret_key, algorithm='HS256')
    
    # Convert bytes to string if necessary
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    
    return jsonify({
        "user": user.to_dict(),
        "token": token
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Log in a user"""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    # Check required fields
    if 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email and password are required"}), 400
    
    # Get auth manager
    auth_manager = get_auth_manager()
    
    # Authenticate user
    user, error = auth_manager.authenticate_user(
        email=data['email'],
        password=data['password']
    )
    
    if error:
        return jsonify({"error": error}), 401
    
    # Create JWT token
    secret_key = config_manager.get('SECRET_KEY')
    token = jwt.encode({
        'sub': user.id,
        'email': user.email,
        'name': user.name,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, secret_key, algorithm='HS256')
    
    # Convert bytes to string if necessary
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    
    return jsonify({
        "user": user.to_dict(),
        "token": token
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh token without complete re-authentication"""
    # Get token using middleware function
    token = get_token_from_header()
    
    if not token:
        return jsonify({"error": "Token required"}), 401
    
    try:
        # Use middleware function to verify token without checking expiration
        payload = verify_token_with_options(token, {"verify_exp": False})
        
        # Get auth manager
        auth_manager = get_auth_manager()
        
        # Check if user still exists
        user = auth_manager.get_user_by_id(payload['sub'])
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Create new token
        secret_key = config_manager.get('SECRET_KEY')
        new_token = jwt.encode({
            'sub': user.id,
            'email': user.email,
            'name': user.name,
            # Create a longer-lasting token (7 days)
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, secret_key, algorithm='HS256')
        
        # Convert bytes to string if necessary
        if isinstance(new_token, bytes):
            new_token = new_token.decode('utf-8')
        
        return jsonify({
            "token": new_token,
            "user": user.to_dict()
        })
        
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current authenticated user"""
    # Get token using middleware function
    token = get_token_from_header()
    
    if not token:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        # Use middleware function to verify token
        payload = verify_token(token)
        
        # Get auth manager
        auth_manager = get_auth_manager()
        
        # Get user
        user = auth_manager.get_user_by_id(payload['sub'])
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify(user.to_dict())
        
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    
@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Log out user (client deletes token)"""
    # Use middleware function to get token
    token = get_token_from_header()
    
    if not token:
        return jsonify({"error": "Authentication required"}), 401

    # In this simple approach, no server-side action is performed.
    # The client should delete the token after successful logout.
    return jsonify({"message": "Successfully logged out. Please remove token on client side."}), 200