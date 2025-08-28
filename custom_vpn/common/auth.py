# STATUS: done
"""
Authentication and authorization for WhisperTunnel VPN.
Simple key-based authentication for MVP.
"""

import hmac
import hashlib
import time
from typing import Optional
from .crypto import CryptoError


class AuthError(Exception):
    """Raised when authentication fails."""
    pass


def create_auth_token(key: bytes, timestamp: Optional[int] = None) -> bytes:
    """
    Create an authentication token using HMAC.
    
    Args:
        key: Shared secret key
        timestamp: Unix timestamp (current time if None)
        
    Returns:
        bytes: Authentication token
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    # Create message: timestamp as 8-byte big-endian integer
    message = timestamp.to_bytes(8, 'big')
    
    # Create HMAC-SHA256
    token = hmac.new(key, message, hashlib.sha256).digest()
    
    return message + token


def verify_auth_token(token: bytes, key: bytes, max_age: int = 300) -> bool:
    """
    Verify an authentication token.
    
    Args:
        token: Authentication token to verify
        key: Shared secret key
        max_age: Maximum token age in seconds
        
    Returns:
        bool: True if token is valid
    """
    if len(token) < 8 + 32:  # timestamp + HMAC-SHA256
        return False
    
    try:
        # Extract timestamp and HMAC
        timestamp_bytes = token[:8]
        received_hmac = token[8:]
        
        # Verify HMAC
        expected_hmac = hmac.new(key, timestamp_bytes, hashlib.sha256).digest()
        
        if not hmac.compare_digest(received_hmac, expected_hmac):
            return False
        
        # Check timestamp
        timestamp = int.from_bytes(timestamp_bytes, 'big')
        current_time = int(time.time())
        
        if abs(current_time - timestamp) > max_age:
            return False
        
        return True
        
    except Exception:
        return False


class SimpleAuth:
    """Simple authentication handler for MVP."""
    
    def __init__(self, shared_key: bytes):
        self.shared_key = shared_key
    
    def authenticate_client(self, client_token: bytes) -> bool:
        """
        Authenticate a client using their token.
        
        Args:
            client_token: Client's authentication token
            
        Returns:
            bool: True if client is authenticated
        """
        return verify_auth_token(client_token, self.shared_key)
    
    def create_client_token(self) -> bytes:
        """
        Create an authentication token for client.
        
        Returns:
            bytes: Authentication token
        """
        return create_auth_token(self.shared_key)


def authenticate_connection(sock, key: bytes, is_server: bool) -> bool:
    """
    Perform authentication handshake over a socket.
    
    Args:
        sock: Socket connection
        key: Shared secret key
        is_server: True if this is the server side
        
    Returns:
        bool: True if authentication successful
        
    Raises:
        AuthError: If authentication fails
    """
    try:
        if is_server:
            # Server: receive and verify client token
            token_data = sock.recv(1024)
            if not token_data:
                raise AuthError("No authentication token received")
            
            if not verify_auth_token(token_data, key):
                raise AuthError("Invalid authentication token")
            
            # Send acknowledgment
            ack_token = create_auth_token(key)
            sock.send(ack_token)
            
        else:
            # Client: send authentication token
            token = create_auth_token(key)
            sock.send(token)
            
            # Receive server acknowledgment
            ack_data = sock.recv(1024)
            if not ack_data:
                raise AuthError("No authentication acknowledgment received")
            
            if not verify_auth_token(ack_data, key):
                raise AuthError("Invalid authentication acknowledgment")
        
        return True
        
    except Exception as e:
        raise AuthError(f"Authentication failed: {e}")
