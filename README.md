# WhisperTunnel VPN

A minimal, educational VPN implementation in Python using TUN interfaces and AES-GCM encryption.

## ⚠️ Educational Purpose Only

This project is designed for **learning purposes only** and should **not be used in production environments**. It demonstrates the fundamental concepts of VPN tunneling but lacks many security features required for real-world use.

## Features

- **Encrypted Tunneling**: AES-GCM encryption with random nonces
- **TUN Interface**: Raw IP packet forwarding via TUN devices
- **Network Namespaces**: Isolated testing using Linux network namespaces
- **TCP Transport**: Reliable packet delivery (UDP support planned)
- **Simple Authentication**: HMAC-based connection authentication

## Architecture

```
Client Namespace                    Server Namespace
┌─────────────────┐                ┌─────────────────┐
│   Application   │                │   Application   │
│        │        │                │        │        │
│     TUN tun0    │                │     TUN tun0    │
│   10.8.0.2/24   │                │   10.8.0.1/24   │
└─────────┬───────┘                └─────────┬───────┘
          │                                  │
    ┌─────▼─────┐                      ┌─────▼─────┐
    │  Client   │─────TCP/5555─────────│  Server   │
    │ (Encrypt) │    192.168.100.x     │ (Decrypt) │
    └───────────┘                      └───────────┘
```

## Quick Start

### Prerequisites

- Linux system with `/dev/net/tun` support
- Python 3.10+
- Root privileges (for TUN interface creation)
- Required packages: `cryptography`, `pyroute2`

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd WhisperTunnel/custom_vpn
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Generate configuration files:
   ```bash
   python3 generate_config.py
   ```

4. Set up network namespaces:
   ```bash
   sudo bash scripts/netns_setup.sh
   ```

### Running the VPN

1. **Start the server** (in one terminal):
   ```bash
   sudo ip netns exec vpn-server python3 server/server.py --config config/server.json
   ```

2. **Start the client** (in another terminal):
   ```bash
   sudo ip netns exec vpn-client python3 client/client.py --config config/client.json
   ```

3. **Test the tunnel**:
   ```bash
   sudo ip netns exec vpn-client ping 10.8.0.1
   ```

### Optional: Internet Access via VPN

To enable internet access through the VPN tunnel:

```bash
sudo bash scripts/server_nat.sh
sudo ip netns exec vpn-client curl http://httpbin.org/ip
```

## Project Structure

```
custom_vpn/
├── client/
│   ├── client.py        # Main client orchestrator
│   ├── tunnel.py        # Client TUN management
│   └── crypto.py        # Client crypto functions
├── server/
│   ├── server.py        # Main server orchestrator
│   ├── tunnel.py        # Server TUN management
│   └── crypto.py        # Server crypto functions
├── common/
│   ├── constants.py     # Shared constants
│   ├── crypto.py        # AES-GCM encryption
│   ├── tunnel.py        # TUN interface management
│   ├── protocol.py      # TCP packet framing
│   ├── auth.py          # Authentication helpers
│   └── utils.py         # Utility functions
├── config/
│   ├── client.json      # Client configuration
│   └── server.json      # Server configuration
├── scripts/
│   ├── netns_setup.sh   # Network namespace setup
│   └── server_nat.sh    # NAT configuration
├── tests/
│   ├── test_crypto.py   # Crypto module tests
│   ├── test_tunnel.py   # TUN interface tests
│   └── test_end2end.py  # Integration tests
└── requirements.txt     # Python dependencies
```

## Configuration

### Client Configuration (`config/client.json`)

```json
{
  "server_host": "192.168.100.1",
  "server_port": 5555,
  "key_base64": "Base64EncodedKey==",
  "tun_addr": "10.8.0.2/24",
  "mtu": 1400
}
```

### Server Configuration (`config/server.json`)

```json
{
  "bind_host": "0.0.0.0",
  "bind_port": 5555,
  "key_base64": "Base64EncodedKey==",
  "tun_addr": "10.8.0.1/24",
  "mtu": 1400,
  "allow_subnet": "10.8.0.0/24"
}
```

## Security Features

- **AES-GCM Encryption**: 256-bit keys with authenticated encryption
- **Random Nonces**: Each packet uses a unique 96-bit nonce
- **Authentication Tags**: Tamper detection via AEAD
- **HMAC Authentication**: Connection-level authentication
- **No Nonce Reuse**: Cryptographically secure random nonce generation

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run specific test modules
pytest tests/test_crypto.py -v
pytest tests/test_tunnel.py -v  # Requires root
pytest tests/test_end2end.py -v # Requires root
```

## Limitations & Known Issues

This is an **educational implementation** with several limitations:

### Security Limitations
- No perfect forward secrecy
- No key rotation mechanism
- Single shared key for all clients
- No replay protection
- Basic authentication only
- No protection against traffic analysis

### Implementation Limitations
- Single client support only
- TCP transport only (higher latency)
- No automatic reconnection
- Basic error handling
- Linux-only support
- Requires root privileges

### Performance Limitations
- No optimization for high throughput
- Single-threaded packet processing
- No packet batching
- No compression

## Educational Value

This project demonstrates:

1. **VPN Fundamentals**: How VPNs create encrypted tunnels
2. **TUN Interfaces**: Low-level packet capture and injection
3. **Cryptography**: Practical use of AEAD encryption
4. **Network Programming**: Socket programming and packet framing
5. **System Programming**: Network namespaces and routing
6. **Protocol Design**: Simple tunnel protocol implementation

## Future Enhancements

- [ ] UDP transport for lower latency
- [ ] Multi-client support
- [ ] Key rotation mechanism
- [ ] Replay protection
- [ ] Perfect forward secrecy
- [ ] Traffic obfuscation
- [ ] Performance optimizations
- [ ] Cross-platform support

## Troubleshooting

### Common Issues

**Permission denied accessing /dev/net/tun**:
```bash
# Ensure TUN module is loaded
sudo modprobe tun
# Run with root privileges
sudo python3 client/client.py --config config/client.json
```

**Network namespace not found**:
```bash
# Run the namespace setup script
sudo bash scripts/netns_setup.sh
```

**Connection refused**:
- Ensure server is running first
- Check firewall settings
- Verify server_host/port in client config

**Ping fails through tunnel**:
- Check TUN interface IPs with `ip addr show tun0`
- Verify routing with `ip route show`
- Check tunnel logs for errors

### Debugging

Enable debug logging:
```bash
python3 client/client.py --config config/client.json --log-level DEBUG
```

Monitor network traffic:
```bash
# Monitor TUN interface
sudo tcpdump -i tun0

# Monitor veth interfaces
sudo ip netns exec vpn-client tcpdump -i veth-c
```

## Cleanup

To clean up the environment:

```bash
# Remove network namespaces
sudo bash scripts/netns_setup.sh cleanup

# Remove NAT rules
sudo bash scripts/server_nat.sh cleanup
```

## License

This project is for educational purposes. Use at your own risk.

## Contributing

This is an educational project. Contributions that improve the learning experience are welcome:

- Better documentation
- More comprehensive tests
- Code clarity improvements
- Additional educational examples

## Acknowledgments

- Inspired by real VPN implementations like WireGuard and OpenVPN
- Uses the `cryptography` library for secure AEAD encryption
- Built for learning about VPN internals and network programming
