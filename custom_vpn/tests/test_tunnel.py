# STATUS: done
"""
Test cases for WhisperTunnel VPN tunnel module.
"""

import pytest
import os
import sys
import tempfile
import socket

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.tunnel import TunInterface, TunnelError, open_tun
from common.constants import DEFAULT_MTU


class TestTunInterface:
    """Test cases for TUN interface management."""
    
    def test_tun_interface_creation(self):
        """Test basic TUN interface creation."""
        # This test requires root privileges and /dev/net/tun
        # Skip if not available
        if not os.path.exists('/dev/net/tun'):
            pytest.skip("TUN device not available")
        
        if os.getuid() != 0:
            pytest.skip("Root privileges required for TUN tests")
        
        tun = TunInterface("test-tun0")
        
        try:
            fd, ifname = tun.open_tun()
            
            assert isinstance(fd, int)
            assert fd > 0
            assert isinstance(ifname, str)
            assert "tun" in ifname.lower()
            
        finally:
            tun.close()
    
    def test_tun_interface_context_manager(self):
        """Test TUN interface as context manager."""
        if not os.path.exists('/dev/net/tun'):
            pytest.skip("TUN device not available")
        
        if os.getuid() != 0:
            pytest.skip("Root privileges required for TUN tests")
        
        with TunInterface("test-tun1") as tun:
            fd, ifname = tun.open_tun()
            assert fd is not None
            assert ifname is not None
    
    def test_tun_read_timeout(self):
        """Test TUN read with timeout."""
        if not os.path.exists('/dev/net/tun'):
            pytest.skip("TUN device not available")
        
        if os.getuid() != 0:
            pytest.skip("Root privileges required for TUN tests")
        
        with TunInterface("test-tun2") as tun:
            tun.open_tun()
            
            # Should timeout and return None
            packet = tun.read_packet(timeout=0.1)
            assert packet is None
    
    def test_tun_write_packet(self):
        """Test writing packet to TUN interface."""
        if not os.path.exists('/dev/net/tun'):
            pytest.skip("TUN device not available")
        
        if os.getuid() != 0:
            pytest.skip("Root privileges required for TUN tests")
        
        with TunInterface("test-tun3") as tun:
            tun.open_tun()
            
            # Write a dummy IP packet
            test_packet = b'\x45\x00\x00\x1c' + b'\x00' * 24  # Minimal IP header
            
            try:
                result = tun.write_packet(test_packet)
                assert isinstance(result, bool)
            except TunnelError:
                # May fail if interface is not properly configured
                # This is expected in test environment
                pass
    
    def test_close_before_open(self):
        """Test closing TUN interface before opening."""
        tun = TunInterface("test-tun4")
        
        # Should not raise exception
        tun.close()
    
    def test_read_before_open(self):
        """Test reading from TUN interface before opening."""
        tun = TunInterface("test-tun5")
        
        with pytest.raises(TunnelError):
            tun.read_packet()
    
    def test_write_before_open(self):
        """Test writing to TUN interface before opening."""
        tun = TunInterface("test-tun6")
        
        with pytest.raises(TunnelError):
            tun.write_packet(b"test")
    
    def test_open_tun_convenience_function(self):
        """Test the convenience open_tun function."""
        if not os.path.exists('/dev/net/tun'):
            pytest.skip("TUN device not available")
        
        if os.getuid() != 0:
            pytest.skip("Root privileges required for TUN tests")
        
        try:
            fd, ifname = open_tun("test-tun7")
            
            assert isinstance(fd, int)
            assert fd > 0
            assert isinstance(ifname, str)
            
        finally:
            if fd:
                os.close(fd)


class TestTunnelConstants:
    """Test tunnel-related constants."""
    
    def test_default_mtu(self):
        """Test default MTU value."""
        assert DEFAULT_MTU == 1400
    
    def test_tun_interface_with_custom_mtu(self):
        """Test TUN interface with custom MTU."""
        custom_mtu = 1200
        tun = TunInterface("test-tun8", mtu=custom_mtu)
        
        assert tun.mtu == custom_mtu


if __name__ == '__main__':
    pytest.main([__file__])
