# Backend/utils/helpers.py
"""
DEPRECATED: This module is maintained for backward compatibility only.
Import utilities from their specialized modules instead:
- File operations: utils.file_utils
- Performance monitoring: utils.performance_utils
- Error handling: utils.error_handler
"""
import logging
from utils.file_utils import allowed_file as file_utils_allowed_file
from utils.file_utils import get_safe_filepath as file_utils_get_safe_filepath
from utils.file_utils import cleanup_file as file_utils_cleanup_file
from utils.performance_utils import timeout_handler as performance_timeout_handler

logger = logging.getLogger(__name__)

def allowed_file(filename):
    """
    DEPRECATED: Use utils.file_utils.allowed_file() instead.
    """
    logger.warning("DEPRECATED: helpers.allowed_file() is deprecated. Use file_utils.allowed_file() instead.")
    return file_utils_allowed_file(filename)

def get_safe_filepath(document_id, filename):
    """
    DEPRECATED: Use utils.file_utils.get_safe_filepath() instead.
    """
    logger.warning("DEPRECATED: helpers.get_safe_filepath() is deprecated. Use file_utils.get_safe_filepath() instead.")
    return file_utils_get_safe_filepath(document_id, filename)

def timeout_handler(max_seconds=120, cpu_limit=70):
    """
    DEPRECATED: Use utils.performance_utils.timeout_handler() instead.
    """
    logger.warning("DEPRECATED: helpers.timeout_handler() is deprecated. Use performance_utils.timeout_handler() instead.")
    return performance_timeout_handler(max_seconds, cpu_limit)