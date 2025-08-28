# STATUS: done
"""
Protocol handling for WhisperTunnel VPN.
Manages packet framing over TCP connections.
"""

import struct
import socket
from typing import Optional
from .constants import PACKET_HEADER_SIZE, MAX_PACKET_SIZE


class ProtocolError(Exception):
    """Raised when protocol operations fail."""
    pass


def send_packet(sock: socket.socket, data: bytes) -> bool:
    """
    Send a packet over TCP with length prefix.
    
    Args:
        sock: TCP socket
        data: Packet data to send
        
    Returns:
        bool: True if successful
        
    Raises:
        ProtocolError: If send fails
    """
    if len(data) > MAX_PACKET_SIZE:
        raise ProtocolError(f"Packet too large: {len(data)} > {MAX_PACKET_SIZE}")
    
    try:
        # Create length prefix (4 bytes, big-endian)
        length_prefix = struct.pack('>I', len(data))
        
        # Send length prefix + data
        sock.sendall(length_prefix + data)
        return True
        
    except Exception as e:
        raise ProtocolError(f"Failed to send packet: {e}")


def recv_packet(sock: socket.socket, timeout: Optional[float] = None) -> Optional[bytes]:
    """
    Receive a packet from TCP with length prefix.
    
    Args:
        sock: TCP socket
        timeout: Receive timeout in seconds
        
    Returns:
        bytes: Packet data, or None if timeout/connection closed
        
    Raises:
        ProtocolError: If receive fails
    """
    if timeout is not None:
        sock.settimeout(timeout)
    
    try:
        # Receive length prefix
        length_data = _recv_exactly(sock, PACKET_HEADER_SIZE)
        if not length_data:
            return None
        
        # Unpack length
        packet_length = struct.unpack('>I', length_data)[0]
        
        if packet_length > MAX_PACKET_SIZE:
            raise ProtocolError(f"Packet too large: {packet_length} > {MAX_PACKET_SIZE}")
        
        # Receive packet data
        packet_data = _recv_exactly(sock, packet_length)
        if not packet_data or len(packet_data) != packet_length:
            raise ProtocolError("Incomplete packet received")
        
        return packet_data
        
    except socket.timeout:
        return None
    except Exception as e:
        raise ProtocolError(f"Failed to receive packet: {e}")


def _recv_exactly(sock: socket.socket, num_bytes: int) -> bytes:
    """
    Receive exactly num_bytes from socket.
    
    Args:
        sock: TCP socket
        num_bytes: Number of bytes to receive
        
    Returns:
        bytes: Received data
        
    Raises:
        Exception: If connection closed or error occurs
    """
    data = b''
    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))
        if not chunk:
            raise Exception("Connection closed")
        data += chunk
    return data


class PacketFramer:
    """Helper class for framing packets over TCP."""
    
    def __init__(self, sock: socket.socket):
        self.sock = sock
    
    def send(self, data: bytes) -> bool:
        """Send a packet."""
        return send_packet(self.sock, data)
    
    def recv(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Receive a packet."""
        return recv_packet(self.sock, timeout)
