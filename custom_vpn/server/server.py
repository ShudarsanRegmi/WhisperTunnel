# STATUS: done
"""
WhisperTunnel VPN Server
Main server that accepts client connections and manages the encrypted tunnel.
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


class VPNServer:
    """VPN Server that manages encrypted tunnels from clients."""
    
    def __init__(self, config_path: str):
        self.logger = setup_logging()
        self.config = load_config(config_path)
        self.running = False
        self.stats = Stats()
        
        # Validate required config fields
        required_fields = ['bind_host', 'bind_port', 'key', 'tun_addr']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
        
        self.bind_host = self.config['bind_host']
        self.bind_port = self.config['bind_port']
        self.key = self.config['key']
        self.tun_addr = self.config['tun_addr']
        self.mtu = self.config.get('mtu', 1400)
        self.allow_subnet = self.config.get('allow_subnet', '10.8.0.0/24')
        
        # Initialize components
        self.tun = None
        self.server_sock = None
        self.client_sock = None
        self.framer = None
        
        # Threading
        self.tun_to_client_thread = None
        self.client_to_tun_thread = None
        self.accept_thread = None
    
    def setup_server_socket(self) -> socket.socket:
        """
        Set up the server socket to listen for client connections.
        
        Returns:
            socket.socket: Server socket ready to accept connections
        """
        self.logger.info(f"Setting up server socket on {self.bind_host}:{self.bind_port}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.bind_host, self.bind_port))
            sock.listen(1)  # Single client for MVP
            
            self.logger.info(f"Server listening on {self.bind_host}:{self.bind_port}")
            return sock
            
        except Exception as e:
            self.logger.error(f"Failed to set up server socket: {e}")
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
    
    def accept_client_connection(self):
        """
        Accept and authenticate a client connection.
        This runs in a separate thread for MVP (single client).
        """
        self.logger.info("Waiting for client connection")
        
        try:
            client_sock, client_addr = self.server_sock.accept()
            self.logger.info(f"Client connected from {client_addr}")
            
            # Perform authentication
            authenticate_connection(client_sock, self.key, is_server=True)
            
            self.logger.info(f"Client {client_addr} authenticated successfully")
            
            # Set up client connection
            self.client_sock = client_sock
            self.framer = PacketFramer(client_sock)
            
            # Start packet forwarding threads
            self.start_packet_forwarding()
            
        except AuthError as e:
            self.logger.error(f"Client authentication failed: {e}")
            if client_sock:
                client_sock.close()
        except Exception as e:
            self.logger.error(f"Error accepting client: {e}")
            if client_sock:
                client_sock.close()
    
    def start_packet_forwarding(self):
        """Start the packet forwarding threads."""
        if not self.running:
            return
        
        self.logger.info("Starting packet forwarding")
        
        self.tun_to_client_thread = threading.Thread(
            target=self.tun_to_client_loop,
            name="TUN->Client"
        )
        self.client_to_tun_thread = threading.Thread(
            target=self.client_to_tun_loop,
            name="Client->TUN"
        )
        
        self.tun_to_client_thread.start()
        self.client_to_tun_thread.start()
    
    def tun_to_client_loop(self):
        """
        Read packets from TUN interface, encrypt them, and send to client.
        This runs in a separate thread.
        """
        self.logger.info("Starting TUN->Client loop")
        
        while self.running and self.client_sock:
            try:
                # Read packet from TUN with timeout
                packet = self.tun.read_packet(timeout=1.0)
                if packet is None:
                    continue
                
                self.logger.debug(f"Read {len(packet)} bytes from TUN")
                
                # Encrypt packet
                encrypted_packet = encrypt(packet, self.key)
                
                # Send to client
                self.framer.send(encrypted_packet)
                
                self.stats.record_packet_out(len(packet))
                self.logger.debug(f"Sent encrypted packet to client ({len(encrypted_packet)} bytes)")
                
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
                    self.logger.error(f"Unexpected error in TUN->Client loop: {e}")
                    break
        
        self.logger.info("TUN->Client loop stopped")
    
    def client_to_tun_loop(self):
        """
        Receive encrypted packets from client, decrypt them, and write to TUN.
        This runs in a separate thread.
        """
        self.logger.info("Starting Client->TUN loop")
        
        while self.running and self.client_sock:
            try:
                # Receive encrypted packet from client
                encrypted_packet = self.framer.recv(timeout=1.0)
                if encrypted_packet is None:
                    continue
                
                self.logger.debug(f"Received {len(encrypted_packet)} bytes from client")
                
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
                    self.logger.error(f"Unexpected error in Client->TUN loop: {e}")
                    break
        
        self.logger.info("Client->TUN loop stopped")
        
        # Clean up client connection
        if self.client_sock:
            self.client_sock.close()
            self.client_sock = None
            self.framer = None
    
    def start(self):
        """Start the VPN server."""
        try:
            self.logger.info("Starting WhisperTunnel VPN Server")
            
            # Set up signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Set up TUN interface
            self.setup_tunnel()
            
            # Set up server socket
            self.server_sock = self.setup_server_socket()
            
            # Start accepting connections
            self.running = True
            
            self.accept_thread = threading.Thread(
                target=self.accept_client_connection,
                name="Accept"
            )
            self.accept_thread.start()
            
            self.logger.info("VPN server started successfully")
            
            # Main loop - periodically print stats
            while self.running:
                time.sleep(10)
                self.logger.info(str(self.stats))
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Server startup failed: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the VPN server."""
        self.logger.info("Stopping VPN server")
        
        # Stop loops
        self.running = False
        
        # Wait for threads to finish
        if self.accept_thread and self.accept_thread.is_alive():
            self.accept_thread.join(timeout=5)
        if self.tun_to_client_thread and self.tun_to_client_thread.is_alive():
            self.tun_to_client_thread.join(timeout=5)
        if self.client_to_tun_thread and self.client_to_tun_thread.is_alive():
            self.client_to_tun_thread.join(timeout=5)
        
        # Clean up resources
        if self.client_sock:
            self.client_sock.close()
        if self.server_sock:
            self.server_sock.close()
        if self.tun:
            self.tun.close()
        
        self.logger.info(f"Final stats: {self.stats}")
        self.logger.info("VPN server stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}")
        self.running = False


def main():
    """Main entry point for the VPN server."""
    parser = argparse.ArgumentParser(description='WhisperTunnel VPN Server')
    parser.add_argument('--config', '-c', required=True,
                       help='Path to server configuration file')
    parser.add_argument('--log-level', '-l', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    try:
        server = VPNServer(args.config)
        server.start()
    except Exception as e:
        logger = setup_logging()
        logger.error(f"Server failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
