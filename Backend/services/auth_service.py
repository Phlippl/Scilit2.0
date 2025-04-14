import hashlib
import os
import uuid
import json
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class UserService:
    """Service for handling user authentication with persistent storage"""
    
    def __init__(self):
        # Define data directory for user storage
        self.data_dir = os.environ.get('DATA_DIR', './data')
        self.users_file = os.path.join(self.data_dir, 'users.json')
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load users from persistent storage
        self.users = self._load_users()
        
        # Add a sample user for testing if no users exist
        if not self.users:
            self._create_sample_user()
    
    def _load_users(self):
        """Load users from JSON file"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    
                    # Convert to email-indexed dictionary for faster lookups
                    users = {}
                    for user_id, user_data in users_data.items():
                        if 'email' in user_data:
                            users[user_data['email']] = user_data
                    
                    logger.info(f"Loaded {len(users)} users from storage")
                    return users
            else:
                logger.info("No users file found, starting with empty user database")
                return {}
        except Exception as e:
            logger.error(f"Error loading users data: {str(e)}")
            return {}
    
    def _save_users(self):
        """Save users to JSON file"""
        try:
            # Convert to ID-indexed format for storage
            users_to_save = {}
            for user_data in self.users.values():
                if 'id' in user_data:
                    users_to_save[user_data['id']] = user_data
            
            # Create temporary file first for safer writing
            temp_file = f"{self.users_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(users_to_save, f, indent=2, default=str)
            
            # Rename to actual file (atomic operation)
            os.replace(temp_file, self.users_file)
            
            logger.info(f"Saved {len(users_to_save)} users to storage")
            return True
        except Exception as e:
            logger.error(f"Error saving users data: {str(e)}")
            return False
    
    def _create_sample_user(self):
        """Create a sample user for testing"""
        sample_email = os.environ.get('VITE_TEST_USER_EMAIL', 'user@example.com')
        sample_password = os.environ.get('VITE_TEST_USER_PASSWORD', 'password123')
        sample_name = os.environ.get('VITE_TEST_USER_NAME', 'Test User')
        
        if sample_email not in self.users:
            user, _ = self.create_user(
                email=sample_email,
                password=sample_password,
                name=sample_name
            )
            
            if user:
                logger.info(f"Created sample user: {sample_email}")
            else:
                logger.error("Failed to create sample user")
    
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
    
    def create_user(self, email, password, name):
        """Create a new user"""
        # Check if user already exists
        if email in self.users:
            return None, "User with this email already exists"
        
        # Generate password hash and salt
        salt, key = self._hash_password(password)
        
        # Create user object
        user = {
            'id': str(uuid.uuid4()),
            'email': email,
            'password_salt': salt.hex(),
            'password_hash': key.hex(),
            'name': name,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Store user
        self.users[email] = user
        
        # Save to persistent storage
        self._save_users()
        
        # Create user directory for uploads
        upload_folder = os.environ.get('UPLOAD_FOLDER', './uploads')
        user_folder = os.path.join(upload_folder, user['id'])
        os.makedirs(user_folder, exist_ok=True)
        
        # Return user (without sensitive information)
        return {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at']
        }, None
    
    def get_user_by_email(self, email):
        """Get a user by email"""
        user = self.users.get(email)
        
        if not user:
            return None
        
        # Return user (without sensitive information)
        return {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at']
        }
    
    def authenticate_user(self, email, password):
        """Authenticate a user"""
        user = self.users.get(email)
        
        if not user:
            return None, "Invalid email or password"
        
        try:
            # Hash the provided password with the stored salt
            salt = bytes.fromhex(user['password_salt'])
            _, key = self._hash_password(password, salt)
            
            # Convert stored hash from hex
            stored_key = bytes.fromhex(user['password_hash'])
            
            # Check if the password hash matches
            if key != stored_key:
                return None, "Invalid email or password"
            
            # Update last login time
            user['last_login'] = datetime.utcnow()
            self.users[email] = user
            self._save_users()
            
            # Return user (without sensitive information)
            return {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'created_at': user['created_at'],
                'updated_at': user['updated_at']
            }, None
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None, "Authentication failed"
    
    def update_user(self, email, updates):
        """Update user information"""
        if email not in self.users:
            return None, "User not found"
        
        user = self.users[email]
        
        # Update fields
        allowed_fields = ['name', 'email']
        for field, value in updates.items():
            if field in allowed_fields:
                user[field] = value
        
        # Update timestamp
        user['updated_at'] = datetime.utcnow()
        
        # Save changes
        self.users[email] = user
        self._save_users()
        
        # Return updated user
        return {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at']
        }, None
    
    def change_password(self, email, current_password, new_password):
        """Change user password"""
        # Verify current password
        user, error = self.authenticate_user(email, current_password)
        if not user:
            return False, error
        
        # Get full user data
        user_data = self.users[email]
        
        # Generate new password hash
        salt, key = self._hash_password(new_password)
        
        # Update password
        user_data['password_salt'] = salt.hex()
        user_data['password_hash'] = key.hex()
        user_data['updated_at'] = datetime.utcnow()
        
        # Save changes
        self.users[email] = user_data
        self._save_users()
        
        return True, None
    
    def delete_user(self, email, password):
        """Delete a user"""
        # Verify password
        user, error = self.authenticate_user(email, password)
        if not user:
            return False, error
        
        # Remove user
        if email in self.users:
            del self.users[email]
            self._save_users()
            return True, None
        
        return False, "User not found"