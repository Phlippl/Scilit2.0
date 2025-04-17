# Backend/services/authentication/password_utils.py
"""
Utilities für Passwort-Hashing und -Validierung
"""
import os
import hashlib
from typing import Tuple, Union

def hash_password(password: str, salt: Union[bytes, None] = None) -> Tuple[bytes, str]:
    """
    Hasht ein Passwort mit einem Salt
    
    Args:
        password: Zu hashendes Passwort
        salt: Optional vorhandenes Salt (wird generiert wenn None)
        
    Returns:
        tuple: (salt als bytes, password_hash als hex-string)
    """
    if salt is None:
        salt = os.urandom(32)  # Salt generieren
    
    # PBKDF2 mit SHA-256 für Passwort-Hashing
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000  # Anzahl der Iterationen
    )
    
    # Gib das Salt als bytes und den Hash als Hex-String zurück
    return salt, key.hex()

def verify_password(password: str, salt: Union[bytes, str], stored_hash: str) -> bool:
    """
    Verifiziert ein Passwort gegen einen gespeicherten Hash
    
    Args:
        password: Zu verifizierendes Passwort
        salt: Salt als bytes oder hex-string
        stored_hash: Gespeicherter Hash
        
    Returns:
        bool: True wenn das Passwort korrekt ist
    """
    # Konvertiere salt zu bytes wenn es ein hex-string ist
    if isinstance(salt, str):
        salt = bytes.fromhex(salt)
    
    # Hashe das Passwort mit dem vorhandenen Salt
    _, generated_hash = hash_password(password, salt)
    
    # Vergleiche mit dem gespeicherten Hash
    return generated_hash == stored_hash