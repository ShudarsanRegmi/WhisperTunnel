# STATUS: done
"""
Utility functions for WhisperTunnel VPN.
"""

import json
import logging
import base64
from typing import Dict, Any
from .crypto import key_from_base64, key_to_base64, generate_key


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        logging.Logger: Configured logger
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    return logging.getLogger('whisper_tunnel')


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to JSON config file
        
    Returns:
        Dict[str, Any]: Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Validate required fields and convert key from base64
        if 'key_base64' in config:
            config['key'] = key_from_base64(config['key_base64'])
        
        return config
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in config file: {e}")


def save_config(config: Dict[str, Any], config_path: str) -> None:
    """
    Save configuration to JSON file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to save JSON config file
    """
    # Make a copy to avoid modifying the original
    config_copy = config.copy()
    
    # Convert key to base64 for storage
    if 'key' in config_copy:
        config_copy['key_base64'] = key_to_base64(config_copy['key'])
        del config_copy['key']
    
    with open(config_path, 'w') as f:
        json.dump(config_copy, f, indent=2)


def generate_config_template(is_server: bool = False) -> Dict[str, Any]:
    """
    Generate a configuration template.
    
    Args:
        is_server: Whether to generate server config template
        
    Returns:
        Dict[str, Any]: Configuration template
    """
    key = generate_key()
    
    if is_server:
        return {
            "bind_host": "0.0.0.0",
            "bind_port": 5555,
            "key_base64": key_to_base64(key),
            "tun_addr": "10.8.0.1/24",
            "mtu": 1400,
            "allow_subnet": "10.8.0.0/24"
        }
    else:
        return {
            "server_host": "192.168.100.1",
            "server_port": 5555,
            "key_base64": key_to_base64(key),
            "tun_addr": "10.8.0.2/24",
            "mtu": 1400
        }


def parse_ip_cidr(cidr: str) -> tuple[str, int]:
    """
    Parse IP address with CIDR notation.
    
    Args:
        cidr: IP address with CIDR (e.g., "10.8.0.1/24")
        
    Returns:
        tuple[str, int]: (ip_address, prefix_length)
    """
    if '/' in cidr:
        ip, prefix = cidr.split('/', 1)
        return ip.strip(), int(prefix)
    else:
        return cidr.strip(), 32


def format_bytes(num_bytes: int) -> str:
    """
    Format bytes in human readable format.
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        str: Formatted string (e.g., "1.23 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


class Stats:
    """Simple statistics tracker."""
    
    def __init__(self):
        self.packets_in = 0
        self.packets_out = 0
        self.bytes_in = 0
        self.bytes_out = 0
        self.decrypt_failures = 0
    
    def record_packet_in(self, size: int):
        """Record an incoming packet."""
        self.packets_in += 1
        self.bytes_in += size
    
    def record_packet_out(self, size: int):
        """Record an outgoing packet."""
        self.packets_out += 1
        self.bytes_out += size
    
    def record_decrypt_failure(self):
        """Record a decryption failure."""
        self.decrypt_failures += 1
    
    def __str__(self) -> str:
        return (f"Stats: {self.packets_in} in ({format_bytes(self.bytes_in)}), "
                f"{self.packets_out} out ({format_bytes(self.bytes_out)}), "
                f"{self.decrypt_failures} decrypt failures")
