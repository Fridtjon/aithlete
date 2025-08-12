"""
Shared JWT utilities for Python services
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import base64

logger = logging.getLogger(__name__)

class JWTUtils:
    """JWT utility class for Python services"""
    
    def __init__(self, secret_key: str, expiration_seconds: int = 86400):
        self.secret_key = secret_key
        self.expiration_seconds = expiration_seconds
        self.algorithm = "HS256"
    
    def generate_token(self, username: str, user_id: Optional[str] = None) -> str:
        """Generate JWT token"""
        payload = {
            "sub": username,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=self.expiration_seconds)
        }
        
        if user_id:
            payload["userId"] = user_id
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Generated JWT token for user: {username}")
            return token
        except Exception as e:
            logger.error(f"Failed to generate JWT token: {e}")
            raise
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            logger.debug(f"Successfully decoded JWT token for user: {payload.get('sub')}")
            return payload
        except jwt.ExpiredSignatureError:
            logger.error("JWT token has expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid JWT token: {e}")
            raise
    
    def get_username_from_token(self, token: str) -> str:
        """Extract username from token"""
        payload = self.decode_token(token)
        return payload.get("sub")
    
    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """Extract user ID from token"""
        payload = self.decode_token(token)
        return payload.get("userId")
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired"""
        try:
            self.decode_token(token)
            return False
        except jwt.ExpiredSignatureError:
            return True
        except jwt.InvalidTokenError:
            return True
    
    def validate_token(self, token: str) -> bool:
        """Validate JWT token"""
        try:
            self.decode_token(token)
            return True
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return False
    
    @staticmethod
    def extract_token_from_header(auth_header: Optional[str]) -> Optional[str]:
        """Extract JWT token from Authorization header"""
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None


class CredentialEncryption:
    """Utility class for encrypting/decrypting user credentials"""
    
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
    
    def derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from master key and salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(self.master_key)
    
    def encrypt_credential(self, credential: str) -> Dict[str, str]:
        """Encrypt credential data"""
        try:
            from cryptography.fernet import Fernet
            
            # Generate salt and derive key
            salt = os.urandom(16)
            key = self.derive_key(salt)
            
            # Create Fernet cipher
            f = Fernet(base64.urlsafe_b64encode(key))
            
            # Encrypt the credential
            encrypted_data = f.encrypt(credential.encode())
            
            return {
                "encrypted_data": base64.b64encode(encrypted_data).decode(),
                "salt": base64.b64encode(salt).decode()
            }
        except Exception as e:
            logger.error(f"Failed to encrypt credential: {e}")
            raise
    
    def decrypt_credential(self, encrypted_data: str, salt: str) -> str:
        """Decrypt credential data"""
        try:
            from cryptography.fernet import Fernet
            
            # Decode salt and derive key
            salt_bytes = base64.b64decode(salt.encode())
            key = self.derive_key(salt_bytes)
            
            # Create Fernet cipher
            f = Fernet(base64.urlsafe_b64encode(key))
            
            # Decrypt the data
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = f.decrypt(encrypted_bytes)
            
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            raise


# Security constants
class SecurityConstants:
    """Security constants for Python services"""
    
    JWT_HEADER = "Authorization"
    JWT_PREFIX = "Bearer "
    JWT_EXPIRATION_TIME = 86400  # 24 hours in seconds
    
    # User Roles
    ROLE_USER = "ROLE_USER"
    ROLE_ADMIN = "ROLE_ADMIN"
    ROLE_SERVICE = "ROLE_SERVICE"
    
    # Public endpoints
    PUBLIC_ENDPOINTS = [
        "/health",
        "/",
        "/docs",
        "/openapi.json",
        "/api/v1/auth/"
    ]
    
    # Rate limiting
    DEFAULT_RATE_LIMIT = 100  # requests per minute
    AUTH_RATE_LIMIT = 10  # authentication attempts per minute
    
    # Password requirements
    MIN_PASSWORD_LENGTH = 8
    PASSWORD_PATTERN = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"


# Dependency for FastAPI
async def get_current_user_from_token(auth_header: str, jwt_utils: JWTUtils) -> Dict[str, Any]:
    """FastAPI dependency to get current user from JWT token"""
    token = JWTUtils.extract_token_from_header(auth_header)
    if not token:
        raise ValueError("No token provided")
    
    if not jwt_utils.validate_token(token):
        raise ValueError("Invalid token")
    
    payload = jwt_utils.decode_token(token)
    return {
        "username": payload.get("sub"),
        "user_id": payload.get("userId"),
        "payload": payload
    }