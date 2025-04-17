# Backend/services/authentication/user_model.py
"""
Datenmodell für Benutzer
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class User:
    """Benutzerdatenmodell"""
    id: str
    email: str
    name: str
    password_hash: str
    password_salt: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Konvertiert das User-Objekt in ein Dictionary
        
        Args:
            include_sensitive: Ob sensible Daten (Passwort-Hash, Salt) eingeschlossen werden sollen
            
        Returns:
            dict: User-Daten als Dictionary
        """
        result = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        if include_sensitive:
            result.update({
                'password_hash': self.password_hash,
                'password_salt': self.password_salt
            })
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Erstellt ein User-Objekt aus einem Dictionary
        
        Args:
            data: Dictionary mit Benutzerdaten
            
        Returns:
            User: Erstelltes User-Objekt
        """
        # Konvertiere Datums-Strings zu datetime-Objekten
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.rstrip('Z'))
        
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.rstrip('Z'))
        
        last_login = data.get('last_login')
        if isinstance(last_login, str):
            last_login = datetime.fromisoformat(last_login.rstrip('Z'))
        
        return cls(
            id=data.get('id'),
            email=data.get('email'),
            name=data.get('name'),
            password_hash=data.get('password_hash', ''),
            password_salt=data.get('password_salt', ''),
            created_at=created_at or datetime.utcnow(),
            updated_at=updated_at or datetime.utcnow(),
            last_login=last_login
        )