"""Decryption helpers for reading encrypted data.

This module provides convenient helper functions for decrypting encrypted
fields from the database models. These helpers handle the decryption process
and provide graceful fallback when decryption fails.
"""

import logging
from typing import Optional
from uuid import UUID

from app.security.encryption import get_encryption_service, DecryptionError

logger = logging.getLogger(__name__)


async def decrypt_field(
    encrypted_value: Optional[str],
    context_id: Optional[UUID] = None,
) -> Optional[str]:
    """Decrypt an encrypted field value.
    
    Args:
        encrypted_value: Base64-encoded encrypted envelope string
        context_id: Optional context ID (e.g., user_id, repo_id) for context binding
        
    Returns:
        Decrypted plaintext string, or None if decryption fails or value is None
        
    Note:
        This function is designed to fail gracefully. If decryption fails,
        it logs the error and returns None rather than raising an exception.
        This is intentional to prevent application crashes when old data
        cannot be decrypted (e.g., during key rotation).
    """
    if not encrypted_value:
        return None
    
    try:
        encryption_service = get_encryption_service()
        
        # Build associated data from context if provided
        associated_data = str(context_id).encode('utf-8') if context_id else None
        
        decrypted = await encryption_service.decrypt(
            encrypted_value,
            associated_data=associated_data,
        )
        return decrypted
        
    except DecryptionError as e:
        logger.warning("Failed to decrypt field: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error during decryption: %s", e)
        return None


async def decrypt_github_token(
    encrypted_token: Optional[str],
    user_id: UUID,
) -> Optional[str]:
    """Decrypt a GitHub access token.
    
    Args:
        encrypted_token: Base64-encoded encrypted token
        user_id: User ID for context binding
        
    Returns:
        Decrypted token string, or None if decryption fails
    """
    return await decrypt_field(encrypted_token, context_id=user_id)


async def decrypt_content_preview(
    encrypted_preview: Optional[str],
    repo_id: UUID,
) -> Optional[str]:
    """Decrypt a file content preview.
    
    Args:
        encrypted_preview: Base64-encoded encrypted preview
        repo_id: Repository ID for context binding
        
    Returns:
        Decrypted preview string, or None if decryption fails
    """
    return await decrypt_field(encrypted_preview, context_id=repo_id)


async def decrypt_raw_code(
    encrypted_code: Optional[str],
    repo_id: UUID,
) -> Optional[str]:
    """Decrypt a node's raw code.
    
    Args:
        encrypted_code: Base64-encoded encrypted code
        repo_id: Repository ID for context binding
        
    Returns:
        Decrypted code string, or None if decryption fails
    """
    return await decrypt_field(encrypted_code, context_id=repo_id)


def get_decrypted_content(
    encrypted_field: Optional[str],
    plaintext_field: Optional[str],
    context_id: Optional[UUID] = None,
) -> str:
    """Synchronous helper to get decrypted content with fallback.
    
    This is a convenience function for use in synchronous contexts where
    you want to try the encrypted field first, then fall back to the plaintext
    field (for backward compatibility during migration).
    
    Args:
        encrypted_field: Encrypted value (will be decrypted asynchronously)
        plaintext_field: Plaintext fallback value
        context_id: Optional context ID for decryption
        
    Returns:
        For now, returns plaintext_field. This is a placeholder for
        future async integration. Use the async decrypt_field functions
        for actual decryption.
        
    Note:
        This synchronous version is provided for API response serialization
        where async operations are not easily available. In production,
        you should decrypt data before serialization or use async endpoints.
    """
    # During migration, prefer encrypted if available, fall back to plaintext
    # This is a synchronous placeholder - actual decryption should happen
    # in the service layer before reaching this point
    return plaintext_field or ""
