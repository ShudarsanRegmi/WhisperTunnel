#!/usr/bin/env python3
# STATUS: done
"""
WhisperTunnel VPN - Configuration Generator
Generates client and server configuration files with shared keys.
"""

import os
import sys
import argparse

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common.utils import generate_config_template, save_config
from common.crypto import generate_key, key_to_base64


def main():
    """Generate configuration files for WhisperTunnel VPN."""
    parser = argparse.ArgumentParser(description='Generate WhisperTunnel VPN configuration files')
    parser.add_argument('--output-dir', '-o', default='config',
                       help='Output directory for config files')
    parser.add_argument('--server-host', default='192.168.100.1',
                       help='Server host for client config')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate shared key
    shared_key = generate_key()
    shared_key_b64 = key_to_base64(shared_key)
    
    # Generate client config
    client_config = generate_config_template(is_server=False)
    client_config['key_base64'] = shared_key_b64
    client_config['server_host'] = args.server_host
    
    # Generate server config
    server_config = generate_config_template(is_server=True)
    server_config['key_base64'] = shared_key_b64
    
    # Save configs
    client_config_path = os.path.join(args.output_dir, 'client.json')
    server_config_path = os.path.join(args.output_dir, 'server.json')
    
    save_config(client_config, client_config_path)
    save_config(server_config, server_config_path)
    
    print("WhisperTunnel VPN configuration files generated:")
    print(f"  Client config: {client_config_path}")
    print(f"  Server config: {server_config_path}")
    print(f"  Shared key: {shared_key_b64}")
    print("")
    print("Next steps:")
    print("1. Set up network namespaces: sudo bash scripts/netns_setup.sh")
    print("2. Start server: sudo ip netns exec vpn-server python3 server/server.py --config config/server.json")
    print("3. Start client: sudo ip netns exec vpn-client python3 client/client.py --config config/client.json")
    print("4. Test tunnel: sudo ip netns exec vpn-client ping 10.8.0.1")


if __name__ == '__main__':
    main()
