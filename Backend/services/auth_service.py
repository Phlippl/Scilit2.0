import hashlib
import os
import uuid
from datetime import datetime

# In a real application, this would use a database like MongoDB
# For now, we'll use an in-memory dictionary for simplicity
users = {}

class AuthService:
    """Service for handling user authentication"""
    
    def __init__(self):
        # Add a sample user for testing
        self._create_sample_user()
    
    def _create_sample_user(self):
        """Create a sample user for testing"""
        if 'user@example.com' not in users:
            self.create_user(
                email='user@example.com',
                password='password123',
                first_name='Test',
                last_name='User'
            )
    
    def _hash_password(self, password, salt=None):
        """Hash a password with a salt"""
        if salt is None:
            salt = os.urandom(32)  # Generate a new salt
        
        # Use PBKDF2 with SHA-256 for password hashing
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # Number of iterations
        )
        
        return salt, key
    
    def create_user(self, email, password, first_name, last_name):
        """Create a new user"""
        # Generate password hash and salt
        salt, key = self._hash_password(password)
        
        # Create user object
        user = {
            'id': str(uuid.uuid4()),
            'email': email,
            'password_salt': salt,
            'password_hash': key,
            'first_name': first_name,
            'last_name': last_name,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Store user
        users[email] = user
        
        # Return user (without sensitive information)
        return {
            'id': user['id'],
            'email': user['email'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at']
        }
    
    def get_user_by_email(self, email):
        """Get a user by email"""
        user = users.get(email)
        
        if not user:
            return None
        
        # Return user (without sensitive information)
        return {
            'id': user['id'],
            'email': user['email'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at']
        }
    
    def authenticate_user(self, email, password):
        """Authenticate a user"""
        user = users.get(email)
        
        if not user:
            return None
        
        # Hash the provided password with the stored salt
        _, key = self._hash_password(password, user['password_salt'])
        
        # Check if the password hash matches
        if key != user['password_hash']:
            return None
        
        # Return user (without sensitive information)
        return {
            'id': user['id'],
            'email': user['email'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at']
        }
