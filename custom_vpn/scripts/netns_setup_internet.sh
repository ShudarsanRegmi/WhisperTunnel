#!/bin/bash
# STATUS: done
# Alternative setup script that runs server on host for internet access
# This allows proper NAT functionality for internet access through VPN

set -e

# Configuration
CLIENT_NS="vpn-client"
VETH_CLIENT="veth-c"
VETH_HOST="veth-h"
CLIENT_IP="192.168.100.2/24"
HOST_VETH_IP="192.168.100.1/24"

echo "Setting up network for internet-enabled WhisperTunnel VPN..."

# Function to clean up existing setup
cleanup() {
    echo "Cleaning up existing setup..."
    
    # Delete namespace (this also removes interfaces in it)
    ip netns del $CLIENT_NS 2>/dev/null || true
    
    # Remove veth pair if it exists in default namespace
    ip link del $VETH_CLIENT 2>/dev/null || true
    ip link del $VETH_HOST 2>/dev/null || true
    
    echo "Cleanup completed"
}

# Clean up any existing setup
cleanup

# Create client network namespace only
echo "Creating client network namespace..."
ip netns add $CLIENT_NS

# Create veth pair (client <-> host)
echo "Creating veth pair for client connectivity..."
ip link add $VETH_CLIENT type veth peer name $VETH_HOST

# Move client veth to client namespace
echo "Moving client interface to namespace..."
ip link set $VETH_CLIENT netns $CLIENT_NS

# Configure client namespace
echo "Configuring client namespace..."
ip netns exec $CLIENT_NS ip addr add $CLIENT_IP dev $VETH_CLIENT
ip netns exec $CLIENT_NS ip link set $VETH_CLIENT up
ip netns exec $CLIENT_NS ip link set lo up

# Configure host side veth
echo "Configuring host interface..."
ip addr add $HOST_VETH_IP dev $VETH_HOST
ip link set $VETH_HOST up

# Add route for client to reach host
ip netns exec $CLIENT_NS ip route add default via 192.168.100.1 dev $VETH_CLIENT metric 100

# Test connectivity between client and host
echo "Testing connectivity between client and host..."
if ip netns exec $CLIENT_NS ping -c 2 192.168.100.1 >/dev/null 2>&1; then
    echo "✓ Connectivity test passed"
else
    echo "⚠ Connectivity test failed, but setup may still work"
fi

echo ""
echo "Internet-enabled VPN setup completed!"
echo ""
echo "Available namespace:"
ip netns list
echo ""
echo "Client namespace network config:"
ip netns exec $CLIENT_NS ip addr show
echo ""
echo "Host veth interface:"
ip addr show $VETH_HOST
echo ""
echo "To test the VPN with internet access:"
echo "1. In one terminal (server on HOST): sudo python3 server/server.py --config config/server.json"
echo "2. In another terminal (client): sudo ip netns exec $CLIENT_NS python3 client/client.py --config config/client.json"
echo "3. Configure NAT: sudo bash scripts/server_nat.sh"
echo "4. Test tunnel: sudo ip netns exec $CLIENT_NS ping 10.8.0.1"
echo "5. Test internet: sudo ip netns exec $CLIENT_NS curl http://httpbin.org/ip"
echo ""
echo "To clean up: sudo $0 cleanup"

# Handle cleanup argument
if [ "$1" = "cleanup" ]; then
    cleanup
    exit 0
fi
