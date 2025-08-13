"""
Unit tests for credential service
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import base64

from app.services.credential_service import CredentialService


@pytest.fixture
def credential_service():
    """Create a credential service instance for testing"""
    with patch('app.services.credential_service.settings') as mock_settings:
        mock_settings.SECRET_KEY = "test_secret_key_for_testing_only"
        return CredentialService()


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing"""
    return str(uuid.uuid4())


class TestCredentialEncryption:
    """Test credential encryption and decryption functionality"""
    
    def test_encrypt_credential(self, credential_service):
        """Test credential encryption"""
        test_credential = "test_username"
        
        result = credential_service.encrypt_credential(test_credential)
        
        assert "encrypted_data" in result
        assert "salt" in result
        assert isinstance(result["encrypted_data"], str)
        assert isinstance(result["salt"], str)
        
        # Verify base64 encoding
        base64.b64decode(result["encrypted_data"])
        base64.b64decode(result["salt"])
    
    def test_encrypt_decrypt_roundtrip(self, credential_service):
        """Test encryption/decryption roundtrip"""
        original_credential = "my_secret_password"
        
        encrypted = credential_service.encrypt_credential(original_credential)
        decrypted = credential_service.decrypt_credential(
            encrypted["encrypted_data"], 
            encrypted["salt"]
        )
        
        assert decrypted == original_credential
    
    def test_different_salts_produce_different_encryption(self, credential_service):
        """Test that same credential produces different encryption with different salts"""
        credential = "same_password"
        
        encrypted1 = credential_service.encrypt_credential(credential)
        encrypted2 = credential_service.encrypt_credential(credential)
        
        # Same credential should produce different encrypted data due to random salts
        assert encrypted1["encrypted_data"] != encrypted2["encrypted_data"]
        assert encrypted1["salt"] != encrypted2["salt"]
    
    def test_decrypt_with_wrong_salt_fails(self, credential_service):
        """Test that decryption fails with wrong salt"""
        credential = "test_password"
        
        encrypted1 = credential_service.encrypt_credential(credential)
        encrypted2 = credential_service.encrypt_credential("different")
        
        with pytest.raises(Exception):
            credential_service.decrypt_credential(
                encrypted1["encrypted_data"],
                encrypted2["salt"]  # Wrong salt
            )


class TestCredentialStorage:
    """Test credential storage functionality"""
    
    @pytest.mark.asyncio
    async def test_store_new_credentials(self, credential_service, mock_db, sample_user_id):
        """Test storing new credentials"""
        username = "test_user"
        password = "test_password"
        
        # Mock database operations
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        
        with patch('app.models.user.UserCredential') as MockCredential:
            result = await credential_service.store_credentials(
                mock_db, sample_user_id, username, password
            )
        
        assert result is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_existing_credentials(self, credential_service, mock_db, sample_user_id):
        """Test updating existing credentials"""
        username = "test_user"
        password = "test_password"
        
        # Mock existing credential
        existing_credential = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_credential
        mock_db.commit = AsyncMock()
        
        with patch('app.models.user.UserCredential'), \
             patch('sqlalchemy.update') as mock_update:
            
            result = await credential_service.store_credentials(
                mock_db, sample_user_id, username, password
            )
        
        assert result is True
        mock_update.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_existing_credentials(self, credential_service, mock_db, sample_user_id):
        """Test retrieving existing credentials"""
        # Mock stored credential
        mock_credential = MagicMock()
        mock_credential.encrypted_data.decode.return_value = "encrypted_password"
        mock_credential.salt.decode.return_value = "salt_string"
        mock_credential.metadata_ = {
            "username_encrypted": "encrypted_username",
            "username_salt": "username_salt"
        }
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_credential
        
        with patch.object(credential_service, 'decrypt_credential') as mock_decrypt:
            mock_decrypt.side_effect = ["test_password", "test_username"]
            
            result = await credential_service.get_credentials(mock_db, sample_user_id)
        
        assert result == {
            "username": "test_username",
            "password": "test_password"
        }
        assert mock_decrypt.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_credentials(self, credential_service, mock_db, sample_user_id):
        """Test retrieving non-existent credentials"""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await credential_service.get_credentials(mock_db, sample_user_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_credentials(self, credential_service, mock_db, sample_user_id):
        """Test deleting credentials"""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        with patch('sqlalchemy.update'):
            result = await credential_service.delete_credentials(mock_db, sample_user_id)
        
        assert result is True
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_credentials(self, credential_service, mock_db, sample_user_id):
        """Test deleting non-existent credentials"""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        with patch('sqlalchemy.update'):
            result = await credential_service.delete_credentials(mock_db, sample_user_id)
        
        assert result is False
        mock_db.commit.assert_called_once()


class TestCredentialTesting:
    """Test credential validation functionality"""
    
    @pytest.mark.asyncio
    async def test_test_valid_credentials(self, credential_service):
        """Test credential validation with valid credentials"""
        with patch('app.services.credential_service.GarminClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.authenticate = AsyncMock(return_value=True)
            
            result = await credential_service.test_credentials("valid_user", "valid_pass")
        
        assert result is True
        mock_client.authenticate.assert_called_once_with("valid_user", "valid_pass")
    
    @pytest.mark.asyncio
    async def test_test_invalid_credentials(self, credential_service):
        """Test credential validation with invalid credentials"""
        with patch('app.services.credential_service.GarminClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.authenticate = AsyncMock(return_value=False)
            
            result = await credential_service.test_credentials("invalid_user", "invalid_pass")
        
        assert result is False
        mock_client.authenticate.assert_called_once_with("invalid_user", "invalid_pass")
    
    @pytest.mark.asyncio
    async def test_test_credentials_exception(self, credential_service):
        """Test credential validation with exception"""
        with patch('app.services.credential_service.GarminClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.authenticate = AsyncMock(side_effect=Exception("Connection error"))
            
            result = await credential_service.test_credentials("user", "pass")
        
        assert result is False


class TestErrorHandling:
    """Test error handling in credential service"""
    
    @pytest.mark.asyncio
    async def test_store_credentials_database_error(self, credential_service, mock_db, sample_user_id):
        """Test handling database errors during credential storage"""
        mock_db.execute.side_effect = Exception("Database error")
        mock_db.rollback = AsyncMock()
        
        with pytest.raises(Exception):
            await credential_service.store_credentials(
                mock_db, sample_user_id, "user", "pass"
            )
        
        mock_db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_credentials_database_error(self, credential_service, mock_db, sample_user_id):
        """Test handling database errors during credential retrieval"""
        mock_db.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await credential_service.get_credentials(mock_db, sample_user_id)
    
    def test_encrypt_credential_error(self, credential_service):
        """Test handling encryption errors"""
        with patch('app.services.credential_service.secrets.token_bytes') as mock_token:
            mock_token.side_effect = Exception("Encryption error")
            
            with pytest.raises(Exception):
                credential_service.encrypt_credential("test")
    
    def test_decrypt_credential_error(self, credential_service):
        """Test handling decryption errors"""
        with pytest.raises(Exception):
            credential_service.decrypt_credential("invalid_data", "invalid_salt")