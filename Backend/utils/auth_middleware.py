# Backend/utils/auth_middleware.py
"""
Authentication middleware for Flask to reduce code duplication across endpoints.
"""
import os
import jwt
from functools import wraps
from flask import request, jsonify, current_app, g
import logging

logger = logging.getLogger(__name__)

def get_token_from_header():
    """Extract JWT token from Authorization header"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    
    # Validate token format
    if not token or token.count('.') != 2:
        return None
    
    return token

def get_user_id():
    """
    Get user ID from JWT token or X-User-ID header with test user support
    Returns user_id or 'default_user' if not authenticated
    """
    user_id = 'default_user'
    
    # Try to get from Authorization header first
    token = get_token_from_header()
    if token:
        try:
            secret_key = current_app.config.get('SECRET_KEY')
            if not secret_key:
                logger.warning("SECRET_KEY not configured")
                return user_id
                
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('sub', user_id)
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
    
    # Fallback to X-User-ID header
    header_user_id = request.headers.get('X-User-ID')
    if header_user_id:
        user_id = header_user_id
    
    # Test mode handling
    test_user_enabled = os.environ.get('VITE_TEST_USER_ENABLED', 'false').lower() == 'true'
    if test_user_enabled and (user_id == 'default_user'):
        test_user_id = os.environ.get('TEST_USER_ID', 'test-user-id')
        logger.info(f"Using test user ID: {test_user_id}")
        user_id = test_user_id
    
    return user_id

def requires_auth(f):
    """
    Decorator to require authentication for API endpoints
    Sets g.user_id for use in the decorated function
    Returns 401 if no valid authentication is provided
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        
        try:
            # Decode token
            secret_key = current_app.config.get('SECRET_KEY')
            if not secret_key:
                return jsonify({"error": "Server configuration error"}), 500
                
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Store user ID in Flask's g object for use in the view function
            g.user_id = payload.get('sub')
            g.user_email = payload.get('email')
            
            # Call the original function
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({"error": "Authentication failed"}), 401
    
    return decorated

def optional_auth(f):
    """
    Decorator for endpoints that can work with or without authentication
    Sets g.user_id if authenticated, otherwise sets it to 'default_user'
    Never returns 401
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get user ID and set it in g
        g.user_id = get_user_id()
        
        # Call the original function
        return f(*args, **kwargs)
    
    return decorated

def is_admin(f):
    """
    Decorator to require admin privileges
    Must be used with requires_auth
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # This decorator assumes requires_auth has already been applied
        # and g.user_id is set
        
        # In a real application, you would check the user's role in a database
        # For demonstration, we'll use a simple admin user list
        admin_users = os.environ.get('ADMIN_USERS', '').split(',')
        
        if not hasattr(g, 'user_id') or g.user_id not in admin_users:
            return jsonify({"error": "Admin privileges required"}), 403
        
        return f(*args, **kwargs)
    
    return decorated