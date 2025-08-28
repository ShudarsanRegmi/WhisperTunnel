# STATUS: done
"""
WhisperTunnel VPN Client
Main client orchestrator that connects to server and manages the encrypted tunnel.
"""

import sys
import os
import socket
import threading
import signal
import argparse
import time
import select

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.tunnel import TunInterface, TunnelError
from common.crypto import encrypt, decrypt, CryptoError
from common.protocol import PacketFramer, ProtocolError
from common.auth import authenticate_connection, AuthError
from common.utils import setup_logging, load_config, parse_ip_cidr, Stats


class VPNClient:
    """VPN Client that manages encrypted tunnel to server."""
    
    def __init__(self, config_path: str):
        self.logger = setup_logging()
        self.config = load_config(config_path)
        self.running = False
        self.stats = Stats()
        
        # Validate required config fields
        required_fields = ['server_host', 'server_port', 'key', 'tun_addr']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
        
        self.server_host = self.config['server_host']
        self.server_port = self.config['server_port']
        self.key = self.config['key']
        self.tun_addr = self.config['tun_addr']
        self.mtu = self.config.get('mtu', 1400)
        
        # Initialize components
        self.tun = None
        self.sock = None
        self.framer = None
        
        # Threading
        self.tun_to_sock_thread = None
        self.sock_to_tun_thread = None
    
    def connect_to_server(self) -> socket.socket:
        """
        Connect to the VPN server and perform authentication.
        
        Returns:
            socket.socket: Connected and authenticated socket
            
        Raises:
            Exception: If connection or authentication fails
        """
        self.logger.info(f"Connecting to server {self.server_host}:{self.server_port}")
        
        try:
            # Create TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server_host, self.server_port))
            
            # Perform authentication
            authenticate_connection(sock, self.key, is_server=False)
            
            self.logger.info("Successfully connected and authenticated to server")
            return sock
            
        except Exception as e:
            self.logger.error(f"Failed to connect to server: {e}")
            if sock:
                sock.close()
            raise
    
    def setup_tunnel(self):
        """Set up the TUN interface."""
        self.logger.info("Setting up TUN interface")
        
        try:
            self.tun = TunInterface("tun0", self.mtu)
            fd, ifname = self.tun.open_tun()
            
            # Configure IP address
            ip_addr, prefix = parse_ip_cidr(self.tun_addr)
            self.tun.configure_ip(ip_addr)
            
            self.logger.info(f"TUN interface {ifname} configured with IP {self.tun_addr}")
            
        except Exception as e:
            self.logger.error(f"Failed to set up TUN interface: {e}")
            raise
    
    def tun_to_socket_loop(self):
        """
        Read packets from TUN interface, encrypt them, and send to server.
        This runs in a separate thread.
        """
        self.logger.info("Starting TUN->Socket loop")
        
        while self.running:
            try:
                # Read packet from TUN with timeout
                packet = self.tun.read_packet(timeout=1.0)
                if packet is None:
                    continue
                
                self.logger.debug(f"Read {len(packet)} bytes from TUN")
                
                # Encrypt packet
                encrypted_packet = encrypt(packet, self.key)
                
                # Send to server
                self.framer.send(encrypted_packet)
                
                self.stats.record_packet_out(len(packet))
                self.logger.debug(f"Sent encrypted packet to server ({len(encrypted_packet)} bytes)")
                
            except TunnelError as e:
                if self.running:
                    self.logger.error(f"TUN error: {e}")
                    break
            except (ProtocolError, socket.error) as e:
                if self.running:
                    self.logger.error(f"Network error: {e}")
                    break
            except CryptoError as e:
                self.logger.error(f"Encryption error: {e}")
                self.stats.record_decrypt_failure()
            except Exception as e:
                if self.running:
                    self.logger.error(f"Unexpected error in TUN->Socket loop: {e}")
                    break
        
        self.logger.info("TUN->Socket loop stopped")
    
    def socket_to_tun_loop(self):
        """
        Receive encrypted packets from server, decrypt them, and write to TUN.
        This runs in a separate thread.
        """
        self.logger.info("Starting Socket->TUN loop")
        
        while self.running:
            try:
                # Receive encrypted packet from server
                encrypted_packet = self.framer.recv(timeout=1.0)
                if encrypted_packet is None:
                    continue
                
                self.logger.debug(f"Received {len(encrypted_packet)} bytes from server")
                
                # Decrypt packet
                packet = decrypt(encrypted_packet, self.key)
                
                # Write to TUN
                self.tun.write_packet(packet)
                
                self.stats.record_packet_in(len(packet))
                self.logger.debug(f"Wrote decrypted packet to TUN ({len(packet)} bytes)")
                
            except (ProtocolError, socket.error) as e:
                if self.running:
                    self.logger.error(f"Network error: {e}")
                    break
            except CryptoError as e:
                self.logger.error(f"Decryption error: {e}")
                self.stats.record_decrypt_failure()
            except TunnelError as e:
                if self.running:
                    self.logger.error(f"TUN error: {e}")
                    break
            except Exception as e:
                if self.running:
                    self.logger.error(f"Unexpected error in Socket->TUN loop: {e}")
                    break
        
        self.logger.info("Socket->TUN loop stopped")
    
    def start(self):
        """Start the VPN client."""
        try:
            self.logger.info("Starting WhisperTunnel VPN Client")
            
            # Set up signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Connect to server
            self.sock = self.connect_to_server()
            self.framer = PacketFramer(self.sock)
            
            # Set up TUN interface
            self.setup_tunnel()
            
            # Start packet forwarding
            self.running = True
            
            self.tun_to_sock_thread = threading.Thread(
                target=self.tun_to_socket_loop,
                name="TUN->Socket"
            )
            self.sock_to_tun_thread = threading.Thread(
                target=self.socket_to_tun_loop,
                name="Socket->TUN"
            )
            
            self.tun_to_sock_thread.start()
            self.sock_to_tun_thread.start()
            
            self.logger.info("VPN client started successfully")
            
            # Main loop - periodically print stats
            while self.running:
                time.sleep(10)
                self.logger.info(str(self.stats))
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Client startup failed: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the VPN client."""
        self.logger.info("Stopping VPN client")
        
        # Stop loops
        self.running = False
        
        # Wait for threads to finish
        if self.tun_to_sock_thread and self.tun_to_sock_thread.is_alive():
            self.tun_to_sock_thread.join(timeout=5)
        if self.sock_to_tun_thread and self.sock_to_tun_thread.is_alive():
            self.sock_to_tun_thread.join(timeout=5)
        
        # Clean up resources
        if self.tun:
            self.tun.close()
        if self.sock:
            self.sock.close()
        
        self.logger.info(f"Final stats: {self.stats}")
        self.logger.info("VPN client stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}")
        self.running = False


def main():
    """Main entry point for the VPN client."""
    parser = argparse.ArgumentParser(description='WhisperTunnel VPN Client')
    parser.add_argument('--config', '-c', required=True,
                       help='Path to client configuration file')
    parser.add_argument('--log-level', '-l', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    try:
        client = VPNClient(args.config)
        client.start()
    except Exception as e:
        logger = setup_logging()
        logger.error(f"Client failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
