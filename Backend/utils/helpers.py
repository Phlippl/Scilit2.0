# Backend/utils/helpers.py
"""
Various helper functions for the SciLit2.0 backend with centralized implementations
"""
import re
import os
import logging
import threading
import time
import psutil
import functools
from flask import current_app
from werkzeug.utils import secure_filename
from typing import Optional, Dict, List, Any

# Import refactored utility modules
from utils.identifier_utils import extract_doi, extract_isbn
from utils.author_utils import format_authors
from utils.metadata_utils import format_metadata_for_storage, normalize_date

logger = logging.getLogger(__name__)

def allowed_file(filename: str) -> bool:
    """
    Check if file extension is allowed
    
    Args:
        filename: The filename
        
    Returns:
        bool: True if file is allowed, else False
    """
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_safe_filepath(document_id: str, filename: str) -> str:
    """
    Create a safe file path for uploaded files
    
    Args:
        document_id: Document ID
        filename: Original filename
        
    Returns:
        str: Safe file path
    """
    # Ensure upload folder exists
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    
    safe_filename = secure_filename(filename)
    return os.path.join(upload_folder, f"{document_id}_{safe_filename}")

def timeout_handler(max_seconds=120, cpu_limit=70):
    """
    Decorator to limit function execution time and CPU usage
    
    Args:
        max_seconds: Maximum execution time in seconds
        cpu_limit: CPU usage limit in percent
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            error = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e
            
            # Start function in a separate thread
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            
            # Monitor execution time and CPU usage
            start_time = time.time()
            process = psutil.Process(os.getpid())
            
            while thread.is_alive():
                thread.join(timeout=1.0)
                elapsed = time.time() - start_time
                
                # Check time limit
                if elapsed > max_seconds:
                    error[0] = TimeoutError(f"Function execution exceeded {max_seconds} seconds")
                    break
                
                # Check CPU usage
                try:
                    cpu_percent = process.cpu_percent(interval=0.5)
                    if cpu_percent > cpu_limit:
                        error[0] = Exception(f"CPU usage too high: {cpu_percent}% (limit: {cpu_limit}%)")
                        break
                except Exception:
                    pass
            
            if error[0]:
                raise error[0]
            
            return result[0]
        
        return wrapper
    return decorator