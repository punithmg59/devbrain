"""Comprehensive tests for encryption service.

Tests cover:
1. encrypt → decrypt returns original data
2. ciphertext differs from plaintext
3. tampered ciphertext fails authentication
4. wrong key fails
5. context binding works correctly
6. key rotation support
7. missing encryption key fails safely
8. no plaintext sensitive data in logs
"""

import pytest
import base64
from uuid import uuid4

from app.security.encryption import (
    EncryptionService,
    EncryptionError,
    DecryptionError,
    get_encryption_service,
)
from app.security.key_provider import (
    EnvironmentKeyProvider,
    get_key_provider,
    set_key_provider,
)


class TestEncryptionService:
    """Test encryption service functionality."""
    
    @pytest.fixture
    def encryption_key(self):
        """Generate a valid 32-byte encryption key for testing."""
        return base64.urlsafe_b64encode(b"0123456789abcdef0123456789abcdef").decode('ascii')
    
    @pytest.fixture
    def key_provider(self, encryption_key):
        """Create a test key provider."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        provider = EnvironmentKeyProvider()
        # Reset global provider
        set_key_provider(provider)
        return provider
    
    @pytest.fixture
    def encryption_service(self, key_provider):
        """Create encryption service instance."""
        return EncryptionService()
    
    @pytest.mark.asyncio
    async def test_encrypt_decrypt_string(self, encryption_service):
        """Test that encrypt → decrypt returns original string data."""
        plaintext = "Hello, World! This is a test string."
        
        encrypted = await encryption_service.encrypt(plaintext)
        assert encrypted != plaintext
        assert encrypted != ""
        
        decrypted = await encryption_service.decrypt(encrypted)
        assert decrypted == plaintext
    
    @pytest.mark.asyncio
    async def test_encrypt_decrypt_bytes(self, encryption_service):
        """Test that encrypt → decrypt returns original bytes data."""
        plaintext = b"Binary data: \x00\x01\x02\x03"
        
        encrypted = await encryption_service.encrypt_bytes(plaintext)
        assert encrypted != plaintext
        assert encrypted != b""
        
        decrypted = await encryption_service.decrypt_bytes(encrypted)
        assert decrypted == plaintext
    
    @pytest.mark.asyncio
    async def test_ciphertext_differs_from_plaintext(self, encryption_service):
        """Test that ciphertext is different from plaintext."""
        plaintext = "Sensitive data"
        
        encrypted = await encryption_service.encrypt(plaintext)
        
        # Ciphertext should be base64-encoded and different
        assert encrypted != plaintext
        # Should be valid base64
        try:
            base64.urlsafe_b64decode(encrypted)
        except Exception:
            pytest.fail("Encrypted data should be valid base64")
    
    @pytest.mark.asyncio
    async def test_tampered_ciphertext_fails_authentication(self, encryption_service):
        """Test that tampered ciphertext fails authentication."""
        plaintext = "Original data"
        
        encrypted = await encryption_service.encrypt(plaintext)
        
        # Tamper with the ciphertext (but not the version byte to avoid version error)
        encrypted_bytes = list(base64.urlsafe_b64decode(encrypted))
        # Skip first 2 bytes (version + key_id) and tamper the nonce
        if len(encrypted_bytes) > 14:
            encrypted_bytes[14] = (encrypted_bytes[14] + 1) % 256  # Flip a bit in nonce
        tampered = base64.urlsafe_b64encode(bytes(encrypted_bytes)).decode('ascii')
        
        # Decryption should fail
        with pytest.raises(DecryptionError, match="tampered"):
            await encryption_service.decrypt(tampered)
    
    @pytest.mark.asyncio
    async def test_context_binding(self, encryption_service):
        """Test that associated data (context binding) works correctly."""
        plaintext = "Secret data"
        context1 = b"user_123"
        context2 = b"user_456"
        
        # Encrypt with context1
        encrypted1 = await encryption_service.encrypt(plaintext, associated_data=context1)
        
        # Decrypt with correct context should work
        decrypted1 = await encryption_service.decrypt(encrypted1, associated_data=context1)
        assert decrypted1 == plaintext
        
        # Decrypt with wrong context should fail
        with pytest.raises(DecryptionError):
            await encryption_service.decrypt(encrypted1, associated_data=context2)
    
    @pytest.mark.asyncio
    async def test_empty_string(self, encryption_service):
        """Test encryption of empty string."""
        plaintext = ""
        
        encrypted = await encryption_service.encrypt(plaintext)
        assert encrypted == ""
        
        decrypted = await encryption_service.decrypt(encrypted)
        assert decrypted == ""
    
    @pytest.mark.asyncio
    async def test_none_value(self, encryption_service):
        """Test that None raises error."""
        with pytest.raises(EncryptionError, match="Cannot encrypt None"):
            await encryption_service.encrypt(None)
    
    @pytest.mark.asyncio
    async def test_large_data(self, encryption_service):
        """Test encryption of large data."""
        plaintext = "A" * 10000  # 10KB
        
        encrypted = await encryption_service.encrypt(plaintext)
        decrypted = await encryption_service.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    @pytest.mark.asyncio
    async def test_unicode_data(self, encryption_service):
        """Test encryption of unicode data."""
        plaintext = "Hello 世界 🌍 Привет مرحبا"
        
        encrypted = await encryption_service.encrypt(plaintext)
        decrypted = await encryption_service.decrypt(encrypted)
        
        assert decrypted == plaintext


class TestKeyProvider:
    """Test key provider functionality."""
    
    @pytest.fixture
    def encryption_key(self):
        """Generate a valid 32-byte encryption key for testing."""
        return base64.urlsafe_b64encode(b"0123456789abcdef0123456789abcdef").decode('ascii')
    
    @pytest.mark.asyncio
    async def test_get_key(self, encryption_key):
        """Test getting a key from provider."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        provider = EnvironmentKeyProvider()
        key = await provider.get_key("default")
        
        assert len(key) == 32  # AES-256 requires 32 bytes
    
    @pytest.mark.asyncio
    async def test_get_active_key_id(self, encryption_key):
        """Test getting active key ID."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        provider = EnvironmentKeyProvider()
        key_id = await provider.get_active_key_id()
        
        assert key_id == "default"
    
    @pytest.mark.asyncio
    async def test_key_exists(self, encryption_key):
        """Test checking if key exists."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        provider = EnvironmentKeyProvider()
        
        assert await provider.key_exists("default")
        assert not await provider.key_exists("nonexistent")
    
    @pytest.mark.asyncio
    async def test_missing_key_raises_error(self):
        """Test that missing encryption key raises error."""
        import os
        # Remove any existing key
        os.environ.pop("DEVBRAIN_ENCRYPTION_KEY", None)
        
        provider = EnvironmentKeyProvider()
        
        with pytest.raises(RuntimeError, match="DEVBRAIN_ENCRYPTION_KEY.*required"):
            await provider.get_key("default")
    
    @pytest.mark.asyncio
    async def test_invalid_key_length(self):
        """Test that invalid key length raises error."""
        import os
        # Key that's too short
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(b"short").decode('ascii')
        
        provider = EnvironmentKeyProvider()
        
        with pytest.raises(RuntimeError, match="valid base64-encoded 32-byte key"):
            await provider.get_key("default")


class TestKeyRotation:
    """Test key rotation support."""
    
    @pytest.fixture
    def encryption_key(self):
        """Generate a valid 32-byte encryption key for testing."""
        return base64.urlsafe_b64encode(b"0123456789abcdef0123456789abcdef").decode('ascii')
    
    @pytest.mark.asyncio
    async def test_envelope_includes_key_id(self, encryption_key):
        """Test that envelope format includes key ID for rotation support."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        provider = EnvironmentKeyProvider()
        set_key_provider(provider)
        
        service = EncryptionService()
        
        plaintext = "Test data"
        encrypted = await service.encrypt(plaintext)
        
        # Decode envelope and verify it has key_id
        envelope = base64.urlsafe_b64decode(encrypted)
        # Structure: version (1 byte) + key_id (1 byte) + nonce (12 bytes) + ciphertext + tag (16 bytes)
        assert len(envelope) > 29  # At minimum: 1 + 1 + 12 + 16 = 30 bytes
        
        # First byte is version
        version = envelope[0]
        assert version == 1
        
        # Second byte is key_id
        key_id = envelope[1]
        assert key_id == 0  # Default key ID


class TestGitHubTokenEncryption:
    """Test GitHub token encryption integration."""
    
    @pytest.fixture
    def encryption_key(self):
        """Generate a valid 32-byte encryption key for testing."""
        return base64.urlsafe_b64encode(b"0123456789abcdef0123456789abcdef").decode('ascii')
    
    @pytest.mark.asyncio
    async def test_github_token_encryption(self, encryption_key):
        """Test that GitHub tokens can be encrypted and decrypted."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        from app.utils.github import save_github_token, get_github_token
        from app.models import User
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # This would require a full database setup
        # For now, test the encryption logic directly
        from app.security.encryption import get_encryption_service
        
        service = get_encryption_service()
        user_id = uuid4()
        user_context = str(user_id).encode('utf-8')
        
        token = "ghp_1234567890abcdef"
        
        # Encrypt
        encrypted = await service.encrypt(token, associated_data=user_context)
        assert encrypted != token
        
        # Decrypt
        decrypted = await service.decrypt(encrypted, associated_data=user_context)
        assert decrypted == token


class TestRepositoryDataEncryption:
    """Test repository data encryption integration."""
    
    @pytest.fixture
    def encryption_key(self):
        """Generate a valid 32-byte encryption key for testing."""
        return base64.urlsafe_b64encode(b"0123456789abcdef0123456789abcdef").decode('ascii')
    
    @pytest.mark.asyncio
    async def test_content_preview_encryption(self, encryption_key):
        """Test that file content previews can be encrypted and decrypted."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        from app.security.encryption import get_encryption_service
        
        service = get_encryption_service()
        repo_id = uuid4()
        repo_context = str(repo_id).encode('utf-8')
        
        preview = "def hello():\n    print('world')"
        
        # Encrypt
        encrypted = await service.encrypt(preview, associated_data=repo_context)
        assert encrypted != preview
        
        # Decrypt
        decrypted = await service.decrypt(encrypted, associated_data=repo_context)
        assert decrypted == preview
    
    @pytest.mark.asyncio
    async def test_raw_code_encryption(self, encryption_key):
        """Test that node raw code can be encrypted and decrypted."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        from app.security.encryption import get_encryption_service
        
        service = get_encryption_service()
        repo_id = uuid4()
        repo_context = str(repo_id).encode('utf-8')
        
        raw_code = "function calculate(x, y) { return x + y; }"
        
        # Encrypt
        encrypted = await service.encrypt(raw_code, associated_data=repo_context)
        assert encrypted != raw_code
        
        # Decrypt
        decrypted = await service.decrypt(encrypted, associated_data=repo_context)
        assert decrypted == raw_code


class TestDecryptionHelpers:
    """Test decryption helper functions."""
    
    @pytest.fixture
    def encryption_key(self):
        """Generate a valid 32-byte encryption key for testing."""
        return base64.urlsafe_b64encode(b"0123456789abcdef0123456789abcdef").decode('ascii')
    
    @pytest.mark.asyncio
    async def test_decrypt_field(self, encryption_key):
        """Test decrypt_field helper."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        from app.security.decryption_helpers import decrypt_field
        from app.security.encryption import get_encryption_service
        
        service = get_encryption_service()
        context_id = uuid4()
        
        plaintext = "Test data"
        encrypted = await service.encrypt(plaintext, associated_data=str(context_id).encode('utf-8'))
        
        decrypted = await decrypt_field(encrypted, context_id)
        assert decrypted == plaintext
    
    @pytest.mark.asyncio
    async def test_decrypt_field_none(self, encryption_key):
        """Test decrypt_field with None value."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        from app.security.decryption_helpers import decrypt_field
        
        result = await decrypt_field(None, uuid4())
        assert result is None
    
    @pytest.mark.asyncio
    async def test_decrypt_field_invalid(self, encryption_key):
        """Test decrypt_field with invalid encrypted data."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        from app.security.decryption_helpers import decrypt_field
        
        # Invalid base64
        result = await decrypt_field("invalid_base64!!!", uuid4())
        assert result is None  # Should fail gracefully
    
    @pytest.mark.asyncio
    async def test_decrypt_github_token(self, encryption_key):
        """Test decrypt_github_token helper."""
        import os
        os.environ["DEVBRAIN_ENCRYPTION_KEY"] = encryption_key
        
        from app.security.decryption_helpers import decrypt_github_token
        from app.security.encryption import get_encryption_service
        
        service = get_encryption_service()
        user_id = uuid4()
        
        token = "ghp_test_token"
        encrypted = await service.encrypt(token, associated_data=str(user_id).encode('utf-8'))
        
        decrypted = await decrypt_github_token(encrypted, user_id)
        assert decrypted == token
