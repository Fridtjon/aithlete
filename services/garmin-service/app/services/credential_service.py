"""
Secure credential storage service for Garmin Connect authentication
"""

import os
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
import structlog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets

from app.core.config import settings

logger = structlog.get_logger(__name__)

class CredentialService:
    """Service for securely storing and retrieving user credentials"""
    
    def __init__(self):
        self.master_key = settings.SECRET_KEY.encode()
    
    def _derive_key(self, salt: bytes) -> bytes:
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
            # Generate random salt
            salt = secrets.token_bytes(16)
            
            # Derive key from master key and salt
            key = self._derive_key(salt)
            
            # Create Fernet cipher
            f = Fernet(base64.urlsafe_b64encode(key))
            
            # Encrypt the credential
            encrypted_data = f.encrypt(credential.encode())
            
            return {
                "encrypted_data": base64.b64encode(encrypted_data).decode(),
                "salt": base64.b64encode(salt).decode()
            }
        except Exception as e:
            logger.error("Failed to encrypt credential", error=str(e))
            raise
    
    def decrypt_credential(self, encrypted_data: str, salt: str) -> str:
        """Decrypt credential data"""
        try:
            # Decode salt and derive key
            salt_bytes = base64.b64decode(salt.encode())
            key = self._derive_key(salt_bytes)
            
            # Create Fernet cipher
            f = Fernet(base64.urlsafe_b64encode(key))
            
            # Decrypt the data
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = f.decrypt(encrypted_bytes)
            
            return decrypted_data.decode()
        except Exception as e:
            logger.error("Failed to decrypt credential", error=str(e))
            raise
    
    async def store_credentials(
        self, 
        db: AsyncSession, 
        user_id: str, 
        username: str, 
        password: str
    ) -> bool:
        """Store encrypted Garmin credentials for a user"""
        try:
            from app.models.user import UserCredential
            
            # Encrypt credentials
            encrypted_username = self.encrypt_credential(username)
            encrypted_password = self.encrypt_credential(password)
            
            # Check if credentials already exist
            result = await db.execute(
                select(UserCredential).where(
                    UserCredential.user_id == user_id,
                    UserCredential.service == 'garmin'
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing credentials
                await db.execute(
                    update(UserCredential)
                    .where(
                        UserCredential.user_id == user_id,
                        UserCredential.service == 'garmin'
                    )
                    .values(
                        encrypted_data=encrypted_password["encrypted_data"].encode(),
                        salt=encrypted_password["salt"].encode(),
                        credential_type='username_password',
                        is_active=True,
                        metadata_={
                            "username_encrypted": encrypted_username["encrypted_data"],
                            "username_salt": encrypted_username["salt"]
                        }
                    )
                )
                logger.info("Updated Garmin credentials", user_id=user_id)
            else:
                # Insert new credentials
                credential = UserCredential(
                    user_id=user_id,
                    service='garmin',
                    credential_type='username_password',
                    encrypted_data=encrypted_password["encrypted_data"].encode(),
                    salt=encrypted_password["salt"].encode(),
                    is_active=True,
                    metadata_={
                        "username_encrypted": encrypted_username["encrypted_data"],
                        "username_salt": encrypted_username["salt"]
                    }
                )
                db.add(credential)
                logger.info("Stored new Garmin credentials", user_id=user_id)
            
            await db.commit()
            return True
            
        except Exception as e:
            logger.error("Failed to store credentials", error=str(e), user_id=user_id)
            await db.rollback()
            raise
    
    async def get_credentials(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> Optional[Dict[str, str]]:
        """Retrieve and decrypt Garmin credentials for a user"""
        try:
            from app.models.user import UserCredential
            
            result = await db.execute(
                select(UserCredential).where(
                    UserCredential.user_id == user_id,
                    UserCredential.service == 'garmin',
                    UserCredential.is_active == True
                )
            )
            credential = result.scalar_one_or_none()
            
            if not credential:
                logger.warning("No Garmin credentials found", user_id=user_id)
                return None
            
            # Decrypt password
            password = self.decrypt_credential(
                credential.encrypted_data.decode(),
                credential.salt.decode()
            )
            
            # Decrypt username from metadata
            username = self.decrypt_credential(
                credential.metadata_["username_encrypted"],
                credential.metadata_["username_salt"]
            )
            
            logger.info("Retrieved Garmin credentials", user_id=user_id)
            return {
                "username": username,
                "password": password
            }
            
        except Exception as e:
            logger.error("Failed to retrieve credentials", error=str(e), user_id=user_id)
            raise
    
    async def delete_credentials(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> bool:
        """Delete Garmin credentials for a user"""
        try:
            from app.models.user import UserCredential
            
            # Mark credentials as inactive instead of deleting for audit trail
            result = await db.execute(
                update(UserCredential)
                .where(
                    UserCredential.user_id == user_id,
                    UserCredential.service == 'garmin'
                )
                .values(is_active=False)
            )
            
            await db.commit()
            
            if result.rowcount > 0:
                logger.info("Deactivated Garmin credentials", user_id=user_id)
                return True
            else:
                logger.warning("No Garmin credentials found to delete", user_id=user_id)
                return False
            
        except Exception as e:
            logger.error("Failed to delete credentials", error=str(e), user_id=user_id)
            await db.rollback()
            raise
    
    async def test_credentials(
        self, 
        username: str, 
        password: str
    ) -> bool:
        """Test if Garmin credentials are valid by attempting authentication"""
        try:
            from app.services.garmin_client import GarminClient
            
            # Create temporary client for testing
            client = GarminClient()
            success = await client.authenticate(username, password)
            
            logger.info("Credential test completed", success=success)
            return success
            
        except Exception as e:
            logger.error("Credential test failed", error=str(e))
            return False

# Global credential service instance
credential_service = CredentialService()