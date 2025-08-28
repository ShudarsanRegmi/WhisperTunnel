#!/bin/bash
# STATUS: done
# Network namespace setup script for WhisperTunnel VPN
# Creates client and server namespaces with veth pair for isolated testing

set -e

# Configuration
CLIENT_NS="vpn-client"
SERVER_NS="vpn-server"
VETH_CLIENT="veth-c"
VETH_SERVER="veth-s"
CLIENT_IP="192.168.100.2/24"
SERVER_IP="192.168.100.1/24"

echo "Setting up network namespaces for WhisperTunnel VPN..."

# Function to clean up existing setup
cleanup() {
    echo "Cleaning up existing setup..."
    
    # Delete namespaces (this also removes interfaces in them)
    ip netns del $CLIENT_NS 2>/dev/null || true
    ip netns del $SERVER_NS 2>/dev/null || true
    
    # Remove veth pair if it exists in default namespace
    ip link del $VETH_CLIENT 2>/dev/null || true
    ip link del $VETH_SERVER 2>/dev/null || true
    
    echo "Cleanup completed"
}

# Clean up any existing setup
cleanup

# Create network namespaces
echo "Creating network namespaces..."
ip netns add $CLIENT_NS
ip netns add $SERVER_NS

# Create veth pair
echo "Creating veth pair..."
ip link add $VETH_CLIENT type veth peer name $VETH_SERVER

# Move veth interfaces to respective namespaces
echo "Moving interfaces to namespaces..."
ip link set $VETH_CLIENT netns $CLIENT_NS
ip link set $VETH_SERVER netns $SERVER_NS

# Configure client namespace
echo "Configuring client namespace..."
ip netns exec $CLIENT_NS ip addr add $CLIENT_IP dev $VETH_CLIENT
ip netns exec $CLIENT_NS ip link set $VETH_CLIENT up
ip netns exec $CLIENT_NS ip link set lo up

# Configure server namespace
echo "Configuring server namespace..."
ip netns exec $SERVER_NS ip addr add $SERVER_IP dev $VETH_SERVER
ip netns exec $SERVER_NS ip link set $VETH_SERVER up
ip netns exec $SERVER_NS ip link set lo up

# Enable IP forwarding in server namespace
echo "Enabling IP forwarding in server namespace..."
ip netns exec $SERVER_NS sysctl -w net.ipv4.ip_forward=1

# Test connectivity between namespaces
echo "Testing connectivity between namespaces..."
if ip netns exec $CLIENT_NS ping -c 2 192.168.100.1 >/dev/null 2>&1; then
    echo "✓ Connectivity test passed"
else
    echo "⚠ Connectivity test failed, but setup may still work"
fi

echo ""
echo "Network namespace setup completed!"
echo ""
echo "Available namespaces:"
ip netns list
echo ""
echo "Client namespace network config:"
ip netns exec $CLIENT_NS ip addr show
echo ""
echo "Server namespace network config:"
ip netns exec $SERVER_NS ip addr show
echo ""
echo "To test the VPN:"
echo "1. In one terminal: sudo ip netns exec $SERVER_NS python3 server/server.py --config config/server.json"
echo "2. In another terminal: sudo ip netns exec $CLIENT_NS python3 client/client.py --config config/client.json"
echo "3. Test tunnel: sudo ip netns exec $CLIENT_NS ping 10.8.0.1"
echo ""
echo "To clean up: sudo $0 cleanup"

# Handle cleanup argument
if [ "$1" = "cleanup" ]; then
    cleanup
    exit 0
fi
