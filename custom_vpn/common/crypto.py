# STATUS: done
"""
Cryptographic functions for WhisperTunnel VPN.
Provides AES-GCM encryption and decryption with random nonces.
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .constants import AES_KEY_SIZE, AES_NONCE_SIZE


class CryptoError(Exception):
    """Raised when cryptographic operations fail."""
    pass


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """
    Encrypt plaintext using AES-GCM with a random nonce.
    
    Args:
        plaintext: The data to encrypt
        key: 32-byte AES key
        
    Returns:
        bytes: nonce (12 bytes) + ciphertext + auth_tag
        
    Raises:
        CryptoError: If encryption fails
    """
    if len(key) != AES_KEY_SIZE:
        raise CryptoError(f"Key must be {AES_KEY_SIZE} bytes, got {len(key)}")
    
    try:
        # Generate random nonce
        nonce = os.urandom(AES_NONCE_SIZE)
        
        # Create AESGCM cipher
        aesgcm = AESGCM(key)
        
        # Encrypt and authenticate
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        # Return nonce + ciphertext (which includes auth tag)
        return nonce + ciphertext
        
    except Exception as e:
        raise CryptoError(f"Encryption failed: {e}")


def decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """
    Decrypt ciphertext using AES-GCM.
    
    Args:
        ciphertext: nonce + encrypted_data + auth_tag
        key: 32-byte AES key
        
    Returns:
        bytes: The decrypted plaintext
        
    Raises:
        CryptoError: If decryption or authentication fails
    """
    if len(key) != AES_KEY_SIZE:
        raise CryptoError(f"Key must be {AES_KEY_SIZE} bytes, got {len(key)}")
    
    if len(ciphertext) < AES_NONCE_SIZE:
        raise CryptoError("Ciphertext too short")
    
    try:
        # Extract nonce and encrypted data
        nonce = ciphertext[:AES_NONCE_SIZE]
        encrypted_data = ciphertext[AES_NONCE_SIZE:]
        
        # Create AESGCM cipher
        aesgcm = AESGCM(key)
        
        # Decrypt and verify
        plaintext = aesgcm.decrypt(nonce, encrypted_data, None)
        
        return plaintext
        
    except Exception as e:
        raise CryptoError(f"Decryption failed: {e}")


def generate_key() -> bytes:
    """Generate a random 32-byte AES key."""
    return os.urandom(AES_KEY_SIZE)


def key_to_base64(key: bytes) -> str:
    """Convert key bytes to base64 string."""
    import base64
    return base64.b64encode(key).decode('ascii')


def key_from_base64(key_b64: str) -> bytes:
    """Convert base64 string to key bytes."""
    import base64
    key = base64.b64decode(key_b64.encode('ascii'))
    if len(key) != AES_KEY_SIZE:
        raise CryptoError(f"Decoded key must be {AES_KEY_SIZE} bytes, got {len(key)}")
    return key
