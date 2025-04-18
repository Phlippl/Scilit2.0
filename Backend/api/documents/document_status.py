# Backend/api/documents/document_status.py
"""
Status tracking module for document processing - redirects to central status service
THIS FILE IS DEPRECATED - Use services.status_service directly instead
"""
import logging
from typing import Dict, Any, Optional, Callable
from services.status_service import get_status_service

logger = logging.getLogger(__name__)

def update_document_status(
    document_id: str, 
    status: str, 
    progress: Optional[int] = None, 
    message: Optional[str] = None, 
    result: Optional[Dict[str, Any]] = None
) -> bool:
    """
    DEPRECATED: Updates document processing status using the central status service
    
    Use get_status_service().update_status() directly instead
    """
    logger.warning(
        "DEPRECATED: update_document_status() is deprecated. "
        "Use get_status_service().update_status() directly instead."
    )
    return get_status_service().update_status(
        status_id=document_id,
        status=status,
        progress=progress,
        message=message,
        result=result
    )

def get_document_status(document_id: str) -> Dict[str, Any]:
    """
    DEPRECATED: Retrieves document processing status from the central status service
    
    Use get_status_service().get_status() directly instead
    """
    logger.warning(
        "DEPRECATED: get_document_status() is deprecated. "
        "Use get_status_service().get_status() directly instead."
    )
    return get_status_service().get_status(document_id)

def register_status_callback(document_id: str, callback: Callable) -> bool:
    """
    DEPRECATED: Registers a callback for status updates
    
    Use get_status_service().register_observer() directly instead
    """
    logger.warning(
        "DEPRECATED: register_status_callback() is deprecated. "
        "Use get_status_service().register_observer() directly instead."
    )
    return get_status_service().register_observer(document_id, callback)

def cleanup_status(document_id: str, delay_seconds: int = 600) -> None:
    """
    DEPRECATED: Cleans up status after delay
    
    Use get_status_service().cleanup_status() directly instead
    """
    logger.warning(
        "DEPRECATED: cleanup_status() is deprecated. "
        "Use get_status_service().cleanup_status() directly instead."
    )
    get_status_service().cleanup_status(document_id, delay_seconds)

def save_status_to_file(document_id: str, status_data: Dict[str, Any]) -> bool:
    """
    DEPRECATED: Legacy function that used to save status to file
    Now uses central status service
    """
    logger.warning(
        "DEPRECATED: save_status_to_file() is deprecated. "
        "Status is now handled by the central status service."
    )
    
    status = status_data.get("status", "unknown")
    progress = status_data.get("progress")
    message = status_data.get("message")
    result = status_data.get("result")
    
    return get_status_service().update_status(
        status_id=document_id,
        status=status,
        progress=progress,
        message=message,
        result=result
    )

def load_status_from_file(document_id: str) -> Optional[Dict[str, Any]]:
    """
    DEPRECATED: Legacy function that used to load status from file
    Now uses central status service
    """
    logger.warning(
        "DEPRECATED: load_status_from_file() is deprecated. "
        "Use get_status_service().get_status() directly instead."
    )
    return get_status_service().get_status(document_id)