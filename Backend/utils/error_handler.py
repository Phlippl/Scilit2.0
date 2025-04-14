# Backend/utils/error_handler.py
"""
Centralized error handling for the Flask application with standardized error responses.
"""
import logging
import traceback
import sys
from flask import jsonify, Blueprint, current_app, g
from werkzeug.exceptions import HTTPException
import requests

# Configure logging
logger = logging.getLogger(__name__)

class APIError(Exception):
    """
    Custom API Exception with status code and optional detail message
    """
    def __init__(self, message, status_code=400, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

def configure_error_handlers(app):
    """
    Configure global error handlers for the Flask application
    
    Args:
        app: Flask application instance
    """
    # Handle custom API errors
    @app.errorhandler(APIError)
    def handle_api_error(error):
        response = {
            'error': error.message
        }
        
        # Add details if available
        if error.details:
            response['details'] = error.details
            
        # Add request ID if available
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
            
        # Log details of the error
        logger.error(f"API Error: {error.message} [Status: {error.status_code}]")
        
        return jsonify(response), error.status_code
    
    # Handle HTTP exceptions (e.g., 404, 405)
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        response = {
            'error': error.description
        }
        
        # Add request ID if available
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
            
        # Log the error
        logger.error(f"HTTP Exception: {error.description} [Status: {error.code}]")
        
        return jsonify(response), error.code
    
    # Handle all unhandled exceptions
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        # In development, include the full traceback
        if app.debug:
            error_details = ''.join(traceback.format_exception(
                type(error), error, error.__traceback__))
            
            response = {
                'error': 'Internal server error',
                'message': str(error),
                'traceback': error_details
            }
        else:
            # In production, only return a generic message
            response = {
                'error': 'Internal server error'
            }
        
        # Add request ID if available
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
        
        # Always log the full traceback
        logger.error(f"Unhandled Exception: {str(error)}", exc_info=True)
        
        return jsonify(response), 500
    
    # Specific error handlers for common cases
    
    # Not Found (404)
    @app.errorhandler(404)
    def not_found(error):
        response = {
            'error': 'Resource not found'
        }
        
        # Add request ID if available
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
            
        return jsonify(response), 404
    
    # Method Not Allowed (405)
    @app.errorhandler(405)
    def method_not_allowed(error):
        response = {
            'error': 'Method not allowed',
            'message': f"The method {requests.method} is not allowed for this endpoint"
        }
        
        # Add request ID if available
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
            
        return jsonify(response), 405
    
    # Payload Too Large (413)
    @app.errorhandler(413)
    def payload_too_large(error):
        max_content_length = current_app.config.get('MAX_CONTENT_LENGTH', 0)
        max_content_length_mb = max_content_length / (1024 * 1024) if max_content_length else 'unknown'
        
        response = {
            'error': 'Payload too large',
            'message': f"The uploaded file exceeds the maximum size of {max_content_length_mb}MB"
        }
        
        # Add request ID if available
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
            
        return jsonify(response), 413

# Helper functions for common API error cases

def bad_request(message, details=None):
    """
    Raise a 400 Bad Request error
    
    Args:
        message: Error message
        details: Optional error details
    
    Raises:
        APIError: with status code 400
    """
    raise APIError(message, status_code=400, details=details)

def unauthorized(message="Authentication required", details=None):
    """
    Raise a 401 Unauthorized error
    
    Args:
        message: Error message
        details: Optional error details
    
    Raises:
        APIError: with status code 401
    """
    raise APIError(message, status_code=401, details=details)

def forbidden(message="Access forbidden", details=None):
    """
    Raise a 403 Forbidden error
    
    Args:
        message: Error message
        details: Optional error details
    
    Raises:
        APIError: with status code 403
    """
    raise APIError(message, status_code=403, details=details)

def not_found(message="Resource not found", details=None):
    """
    Raise a 404 Not Found error
    
    Args:
        message: Error message
        details: Optional error details
    
    Raises:
        APIError: with status code 404
    """
    raise APIError(message, status_code=404, details=details)

def server_error(message="Internal server error", details=None):
    """
    Raise a 500 Internal Server Error
    
    Args:
        message: Error message
        details: Optional error details
    
    Raises:
        APIError: with status code 500
    """
    raise APIError(message, status_code=500, details=details)

# Example usage:
# from utils.error_handler import bad_request, not_found
#
# @app.route('/api/example/<id>')
# def get_example(id):
#     example = db.get_example(id)
#     if not example:
#         not_found(f"Example with ID {id} not found")
#     return jsonify(example)