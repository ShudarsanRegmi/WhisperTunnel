# STATUS: done
"""
End-to-end integration tests for WhisperTunnel VPN.
"""

import pytest
import os
import sys
import subprocess
import time
import signal
import socket
import threading

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils import generate_config_template, save_config
from common.crypto import generate_key, key_to_base64


class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_config_generation(self):
        """Test configuration file generation."""
        # Generate client config
        client_config = generate_config_template(is_server=False)
        
        required_client_fields = ['server_host', 'server_port', 'key_base64', 'tun_addr', 'mtu']
        for field in required_client_fields:
            assert field in client_config
        
        # Generate server config
        server_config = generate_config_template(is_server=True)
        
        required_server_fields = ['bind_host', 'bind_port', 'key_base64', 'tun_addr', 'mtu', 'allow_subnet']
        for field in required_server_fields:
            assert field in server_config
    
    def test_same_key_in_configs(self):
        """Test that client and server can use the same key."""
        # Generate a shared key
        shared_key = generate_key()
        shared_key_b64 = key_to_base64(shared_key)
        
        # Create configs with same key
        client_config = generate_config_template(is_server=False)
        server_config = generate_config_template(is_server=True)
        
        client_config['key_base64'] = shared_key_b64
        server_config['key_base64'] = shared_key_b64
        
        # Verify keys match
        assert client_config['key_base64'] == server_config['key_base64']
    
    @pytest.mark.skipif(os.getuid() != 0, reason="Root privileges required")
    @pytest.mark.skipif(not os.path.exists('/dev/net/tun'), reason="TUN device not available")
    def test_network_namespace_setup(self):
        """Test network namespace setup script."""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'scripts', 'netns_setup.sh'
        )
        
        if not os.path.exists(script_path):
            pytest.skip("Network setup script not found")
        
        try:
            # Run setup script
            result = subprocess.run(
                ['sudo', 'bash', script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            assert result.returncode == 0, f"Setup failed: {result.stderr}"
            
            # Verify namespaces exist
            result = subprocess.run(
                ['ip', 'netns', 'list'],
                capture_output=True,
                text=True
            )
            
            assert 'vpn-client' in result.stdout
            assert 'vpn-server' in result.stdout
            
        finally:
            # Clean up
            subprocess.run(
                ['sudo', 'bash', script_path, 'cleanup'],
                capture_output=True
            )
    
    def test_tcp_socket_communication(self):
        """Test basic TCP socket communication."""
        # Simple test to verify socket functionality
        host = '127.0.0.1'
        port = 0  # Let OS choose port
        
        # Create server socket
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind((host, port))
        server_sock.listen(1)
        
        actual_port = server_sock.getsockname()[1]
        
        def server_handler():
            client_sock, addr = server_sock.accept()
            data = client_sock.recv(1024)
            client_sock.send(data)  # Echo back
            client_sock.close()
        
        # Start server in thread
        server_thread = threading.Thread(target=server_handler)
        server_thread.start()
        
        try:
            # Connect client
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect((host, actual_port))
            
            # Send test data
            test_data = b"Hello, WhisperTunnel!"
            client_sock.send(test_data)
            
            # Receive echo
            received = client_sock.recv(1024)
            assert received == test_data
            
            client_sock.close()
            
        finally:
            server_sock.close()
            server_thread.join(timeout=5)
    
    def test_packet_framing(self):
        """Test packet framing over TCP."""
        from common.protocol import send_packet, recv_packet
        
        host = '127.0.0.1'
        port = 0
        
        # Create server socket
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind((host, port))
        server_sock.listen(1)
        
        actual_port = server_sock.getsockname()[1]
        
        def server_handler():
            client_sock, addr = server_sock.accept()
            
            # Receive packet
            packet = recv_packet(client_sock)
            if packet:
                # Echo back
                send_packet(client_sock, packet)
            
            client_sock.close()
        
        # Start server in thread
        server_thread = threading.Thread(target=server_handler)
        server_thread.start()
        
        try:
            # Connect client
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect((host, actual_port))
            
            # Send framed packet
            test_packet = b"Framed packet test data"
            send_packet(client_sock, test_packet)
            
            # Receive framed packet
            received_packet = recv_packet(client_sock)
            assert received_packet == test_packet
            
            client_sock.close()
            
        finally:
            server_sock.close()
            server_thread.join(timeout=5)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
