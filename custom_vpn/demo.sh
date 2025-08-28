#!/bin/bash
# WhisperTunnel VPN Demo Script
# This script demonstrates the complete setup and testing of WhisperTunnel VPN

set -e

echo "=========================================="
echo "WhisperTunnel VPN Demo"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This demo requires root privileges for TUN interface management."
    echo "Please run with sudo:"
    echo "  sudo bash demo.sh"
    exit 1
fi

echo "1. Setting up network namespaces..."
bash scripts/netns_setup.sh

echo ""
echo "2. Generated configurations:"
cat config/client.json | jq .
echo ""
cat config/server.json | jq .

echo ""
echo "3. Starting VPN server in background..."
ip netns exec vpn-server python3 server/server.py --config config/server.json --log-level INFO &
SERVER_PID=$!

# Give server time to start
sleep 2

echo ""
echo "4. Starting VPN client in background..."
ip netns exec vpn-client python3 client/client.py --config config/client.json --log-level INFO &
CLIENT_PID=$!

# Give client time to connect
sleep 3

echo ""
echo "5. Testing the VPN tunnel..."
echo "Pinging server through the encrypted tunnel..."

if ip netns exec vpn-client ping -c 3 10.8.0.1; then
    echo "✅ VPN tunnel is working!"
else
    echo "❌ VPN tunnel test failed"
fi

echo ""
echo "6. Showing tunnel interface status..."
echo "Client TUN interface:"
ip netns exec vpn-client ip addr show tun0 2>/dev/null || echo "TUN interface not found"

echo ""
echo "Server TUN interface:"
ip netns exec vpn-server ip addr show tun0 2>/dev/null || echo "TUN interface not found"

echo ""
echo "7. Cleaning up..."
kill $CLIENT_PID $SERVER_PID 2>/dev/null || true
sleep 2

echo ""
echo "8. Removing network namespaces..."
bash scripts/netns_setup.sh cleanup

echo ""
echo "Demo completed!"
echo ""
echo "To run the VPN manually:"
echo "1. sudo bash scripts/netns_setup.sh"
echo "2. sudo ip netns exec vpn-server python3 server/server.py --config config/server.json"
echo "3. sudo ip netns exec vpn-client python3 client/client.py --config config/client.json"
echo "4. sudo ip netns exec vpn-client ping 10.8.0.1"
