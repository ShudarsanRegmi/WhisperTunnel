# STATUS: done
"""
Constants used throughout the WhisperTunnel VPN project.
"""

# Network configuration
DEFAULT_MTU = 1400
TUN_DEVICE_NAME = "tun0"

# Crypto configuration
AES_KEY_SIZE = 32  # 256 bits
AES_NONCE_SIZE = 12  # 96 bits for GCM
AES_TAG_SIZE = 16  # 128 bits authentication tag

# Default addresses
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = 5555
DEFAULT_CLIENT_TUN_IP = "10.8.0.2/24"
DEFAULT_SERVER_TUN_IP = "10.8.0.1/24"

# Protocol framing
PACKET_HEADER_SIZE = 4  # Length prefix for TCP framing
MAX_PACKET_SIZE = DEFAULT_MTU + 100  # Account for overhead

# TUN interface flags
import struct
import fcntl

TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000
TUN_FLAGS = IFF_TUN | IFF_NO_PI
