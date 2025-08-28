#!/bin/bash
# STATUS: done
# NAT setup script for WhisperTunnel VPN
# Enables NAT from VPN clients to the internet via server

set -e

# Configuration
SERVER_NS="vpn-server"
VPN_SUBNET="10.8.0.0/24"
HOST_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)

echo "Setting up NAT for WhisperTunnel VPN..."
echo "Host interface: $HOST_INTERFACE"
echo "VPN subnet: $VPN_SUBNET"

# Function to clean up NAT rules
cleanup_nat() {
    echo "Cleaning up NAT rules..."
    
    # Remove iptables rules (ignore errors if they don't exist)
    iptables -t nat -D POSTROUTING -s $VPN_SUBNET -o $HOST_INTERFACE -j MASQUERADE 2>/dev/null || true
    iptables -D FORWARD -i tun0 -o $HOST_INTERFACE -j ACCEPT 2>/dev/null || true
    iptables -D FORWARD -i $HOST_INTERFACE -o tun0 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
    
    # Disable IP forwarding
    sysctl -w net.ipv4.ip_forward=0
    
    echo "NAT cleanup completed"
}

# Handle cleanup argument
if [ "$1" = "cleanup" ]; then
    cleanup_nat
    exit 0
fi

# Check if host interface exists
if [ -z "$HOST_INTERFACE" ]; then
    echo "Error: Could not determine host network interface"
    exit 1
fi

# Enable IP forwarding on host
echo "Enabling IP forwarding on host..."
sysctl -w net.ipv4.ip_forward=1

# Add NAT rule
echo "Adding NAT rule..."
iptables -t nat -I POSTROUTING -s $VPN_SUBNET -o $HOST_INTERFACE -j MASQUERADE

# Add forwarding rules
echo "Adding forwarding rules..."
iptables -I FORWARD -i tun0 -o $HOST_INTERFACE -j ACCEPT
iptables -I FORWARD -i $HOST_INTERFACE -o tun0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# In server namespace, add default route via VPN
echo "Adding routes in server namespace..."
ip netns exec $SERVER_NS ip route add default via 10.8.0.1 dev tun0 metric 100 2>/dev/null || true

echo ""
echo "NAT setup completed!"
echo ""
echo "Current iptables NAT rules:"
iptables -t nat -L POSTROUTING -n --line-numbers | grep $VPN_SUBNET
echo ""
echo "Current iptables FORWARD rules:"
iptables -L FORWARD -n --line-numbers | grep -E "(tun0|$HOST_INTERFACE)"
echo ""
echo "To test internet connectivity:"
echo "sudo ip netns exec vpn-client curl -s http://httpbin.org/ip"
echo ""
echo "To clean up NAT: sudo $0 cleanup"
