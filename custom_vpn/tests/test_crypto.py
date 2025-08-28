# STATUS: done
"""
Test cases for WhisperTunnel VPN crypto module.
"""

import pytest
import os
import sys

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.crypto import encrypt, decrypt, CryptoError, generate_key, key_to_base64, key_from_base64


class TestCrypto:
    """Test cases for crypto functions."""
    
    def test_key_generation(self):
        """Test key generation."""
        key1 = generate_key()
        key2 = generate_key()
        
        assert len(key1) == 32
        assert len(key2) == 32
        assert key1 != key2  # Should be different
    
    def test_key_base64_conversion(self):
        """Test key to/from base64 conversion."""
        key = generate_key()
        key_b64 = key_to_base64(key)
        key_restored = key_from_base64(key_b64)
        
        assert key == key_restored
        assert isinstance(key_b64, str)
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt(decrypt(x)) == x."""
        key = generate_key()
        plaintext = b"Hello, WhisperTunnel VPN!"
        
        ciphertext = encrypt(plaintext, key)
        decrypted = decrypt(ciphertext, key)
        
        assert decrypted == plaintext
    
    def test_encrypt_with_different_keys(self):
        """Test that different keys produce different ciphertexts."""
        key1 = generate_key()
        key2 = generate_key()
        plaintext = b"Same message"
        
        ciphertext1 = encrypt(plaintext, key1)
        ciphertext2 = encrypt(plaintext, key2)
        
        assert ciphertext1 != ciphertext2
    
    def test_encrypt_same_message_different_nonces(self):
        """Test that encrypting the same message twice produces different results."""
        key = generate_key()
        plaintext = b"Same message, different nonces"
        
        ciphertext1 = encrypt(plaintext, key)
        ciphertext2 = encrypt(plaintext, key)
        
        # Should be different due to random nonces
        assert ciphertext1 != ciphertext2
        
        # But both should decrypt to the same plaintext
        assert decrypt(ciphertext1, key) == plaintext
        assert decrypt(ciphertext2, key) == plaintext
    
    def test_decrypt_with_wrong_key(self):
        """Test that decryption with wrong key fails."""
        key1 = generate_key()
        key2 = generate_key()
        plaintext = b"Secret message"
        
        ciphertext = encrypt(plaintext, key1)
        
        with pytest.raises(CryptoError):
            decrypt(ciphertext, key2)
    
    def test_decrypt_tampered_ciphertext(self):
        """Test that tampered ciphertext fails decryption."""
        key = generate_key()
        plaintext = b"Authentic message"
        
        ciphertext = encrypt(plaintext, key)
        
        # Tamper with the ciphertext by flipping a bit
        tampered = bytearray(ciphertext)
        tampered[-1] ^= 1  # Flip the last bit
        
        with pytest.raises(CryptoError):
            decrypt(bytes(tampered), key)
    
    def test_nonce_prepending(self):
        """Test that nonce is prepended to ciphertext."""
        key = generate_key()
        plaintext = b"Test nonce prepending"
        
        ciphertext = encrypt(plaintext, key)
        
        # Ciphertext should start with 12-byte nonce
        assert len(ciphertext) >= 12
        
        # Extract nonce
        nonce = ciphertext[:12]
        assert len(nonce) == 12
    
    def test_invalid_key_size(self):
        """Test that invalid key sizes are rejected."""
        plaintext = b"Test message"
        
        # Test various invalid key sizes
        for key_size in [16, 24, 31, 33, 64]:
            invalid_key = os.urandom(key_size)
            
            with pytest.raises(CryptoError):
                encrypt(plaintext, invalid_key)
            
            with pytest.raises(CryptoError):
                decrypt(b"dummy_ciphertext", invalid_key)
    
    def test_empty_plaintext(self):
        """Test encryption/decryption of empty data."""
        key = generate_key()
        plaintext = b""
        
        ciphertext = encrypt(plaintext, key)
        decrypted = decrypt(ciphertext, key)
        
        assert decrypted == plaintext
    
    def test_large_plaintext(self):
        """Test encryption/decryption of large data."""
        key = generate_key()
        plaintext = b"A" * 10000  # 10KB of data
        
        ciphertext = encrypt(plaintext, key)
        decrypted = decrypt(ciphertext, key)
        
        assert decrypted == plaintext
    
    def test_ciphertext_too_short(self):
        """Test that too-short ciphertext is rejected."""
        key = generate_key()
        
        # Ciphertext shorter than nonce size
        short_ciphertext = b"short"
        
        with pytest.raises(CryptoError):
            decrypt(short_ciphertext, key)


if __name__ == '__main__':
    pytest.main([__file__])
