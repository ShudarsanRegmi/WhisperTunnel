# STATUS: done
"""
TUN interface management for WhisperTunnel VPN.
Handles creation, configuration, and I/O operations on TUN devices.
"""

import os
import fcntl
import struct
import select
import socket
import subprocess
from typing import Tuple, Optional
from .constants import TUNSETIFF, TUN_FLAGS, DEFAULT_MTU


class TunnelError(Exception):
    """Raised when tunnel operations fail."""
    pass


class TunInterface:
    """Manages a TUN interface for packet forwarding."""
    
    def __init__(self, name: str = "tun0", mtu: int = DEFAULT_MTU):
        self.name = name
        self.mtu = mtu
        self.fd = None
        self.ifname = None
    
    def open_tun(self) -> Tuple[int, str]:
        """
        Create and open a TUN interface.
        
        Returns:
            Tuple[int, str]: (file_descriptor, interface_name)
            
        Raises:
            TunnelError: If TUN creation fails
        """
        try:
            # Open TUN device
            self.fd = os.open("/dev/net/tun", os.O_RDWR)
            
            # Configure interface
            ifr = struct.pack('16sH', self.name.encode('utf-8'), TUN_FLAGS)
            fcntl.ioctl(self.fd, TUNSETIFF, ifr)
            
            # Extract the actual interface name (kernel might modify it)
            self.ifname = ifr[:16].decode('utf-8').rstrip('\x00')
            
            # Set non-blocking mode
            fcntl.fcntl(self.fd, fcntl.F_SETFL, os.O_NONBLOCK)
            
            return self.fd, self.ifname
            
        except Exception as e:
            if self.fd:
                os.close(self.fd)
                self.fd = None
            raise TunnelError(f"Failed to create TUN interface: {e}")
    
    def read_packet(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Read a packet from the TUN interface.
        
        Args:
            timeout: Timeout in seconds for select()
            
        Returns:
            bytes: The packet data, or None if timeout/no data
            
        Raises:
            TunnelError: If read operation fails
        """
        if not self.fd:
            raise TunnelError("TUN interface not open")
        
        try:
            # Wait for data with timeout
            ready, _, _ = select.select([self.fd], [], [], timeout)
            if not ready:
                return None
            
            # Read packet
            data = os.read(self.fd, 4096)
            return data
            
        except BlockingIOError:
            return None
        except Exception as e:
            raise TunnelError(f"Failed to read from TUN: {e}")
    
    def write_packet(self, packet: bytes) -> bool:
        """
        Write a packet to the TUN interface.
        
        Args:
            packet: The packet data to write
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            TunnelError: If write operation fails
        """
        if not self.fd:
            raise TunnelError("TUN interface not open")
        
        try:
            bytes_written = os.write(self.fd, packet)
            return bytes_written == len(packet)
            
        except Exception as e:
            raise TunnelError(f"Failed to write to TUN: {e}")
    
    def configure_ip(self, ip_address: str, netmask: str = "255.255.255.0") -> bool:
        """
        Configure IP address on the TUN interface.
        
        Args:
            ip_address: IP address to assign (e.g., "10.8.0.1")
            netmask: Network mask (default: "255.255.255.0")
            
        Returns:
            bool: True if successful
            
        Raises:
            TunnelError: If configuration fails
        """
        if not self.ifname:
            raise TunnelError("TUN interface not created")
        
        try:
            # Bring interface up
            subprocess.run([
                "ip", "link", "set", "dev", self.ifname, "up"
            ], check=True, capture_output=True)
            
            # Add IP address
            subprocess.run([
                "ip", "addr", "add", f"{ip_address}/24", "dev", self.ifname
            ], check=True, capture_output=True)
            
            # Set MTU
            subprocess.run([
                "ip", "link", "set", "dev", self.ifname, "mtu", str(self.mtu)
            ], check=True, capture_output=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            raise TunnelError(f"Failed to configure TUN interface: {e}")
    
    def close(self):
        """Close the TUN interface."""
        if self.fd:
            os.close(self.fd)
            self.fd = None
            self.ifname = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def open_tun(name: str = "tun0") -> Tuple[int, str]:
    """
    Convenience function to create a TUN interface.
    
    Args:
        name: Interface name
        
    Returns:
        Tuple[int, str]: (file_descriptor, interface_name)
    """
    tun = TunInterface(name)
    return tun.open_tun()
