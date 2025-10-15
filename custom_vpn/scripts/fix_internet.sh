#!/bin/bash
# Quick fix script for internet access through WhisperTunnel VPN
# This enables internet access by running server on host instead of in namespace

echo "WhisperTunnel Internet Access Fix"
echo "================================="
echo ""

# Step 1: Stop any existing VPN processes
echo "1. Stopping existing VPN processes..."
sudo pkill -f "server.py" 2>/dev/null || true
sudo pkill -f "client.py" 2>/dev/null || true
sleep 2

# Step 2: Clean up existing namespaces
echo "2. Cleaning up existing setup..."
sudo bash scripts/netns_setup.sh cleanup 2>/dev/null || true

# Step 3: Set up only client namespace
echo "3. Setting up client namespace..."
sudo ip netns add vpn-client
sudo ip link add veth-c type veth peer name veth-h
sudo ip link set veth-c netns vpn-client
sudo ip netns exec vpn-client ip addr add 192.168.100.2/24 dev veth-c
sudo ip netns exec vpn-client ip link set veth-c up
sudo ip netns exec vpn-client ip link set lo up
sudo ip addr add 192.168.100.1/24 dev veth-h
sudo ip link set veth-h up

# Step 4: Configure DNS for client
echo "4. Configuring DNS..."
sudo mkdir -p /etc/netns/vpn-client
echo -e "nameserver 8.8.8.8\nnameserver 1.1.1.1" | sudo tee /etc/netns/vpn-client/resolv.conf >/dev/null

# Step 5: Set up NAT and forwarding
echo "5. Setting up NAT and forwarding..."
sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null
HOST_IF=$(ip route | grep default | awk '{print $5}' | head -n1)
sudo iptables -t nat -I POSTROUTING -s 10.8.0.0/24 -o $HOST_IF -j MASQUERADE 2>/dev/null || true
sudo iptables -t nat -I POSTROUTING -s 192.168.100.0/24 -o $HOST_IF -j MASQUERADE 2>/dev/null || true
sudo iptables -I FORWARD -s 10.8.0.0/24 -j ACCEPT 2>/dev/null || true
sudo iptables -I FORWARD -s 192.168.100.0/24 -j ACCEPT 2>/dev/null || true

echo ""
echo "Setup complete! Now follow these steps:"
echo ""
echo "1. Start SERVER on HOST (in one terminal):"
echo "   cd /home/aparichit/Projects/WhisperTunnel/custom_vpn"
echo "   sudo python3 server/server.py --config config/server.json"
echo ""
echo "2. Start CLIENT in namespace (in another terminal):"
echo "   cd /home/aparichit/Projects/WhisperTunnel/custom_vpn"  
echo "   sudo ip netns exec vpn-client python3 client/client.py --config config/client.json"
echo ""
echo "3. Test tunnel (in third terminal):"
echo "   sudo ip netns exec vpn-client ping 10.8.0.1"
echo ""
echo "4. Test internet access:"
echo "   sudo ip netns exec vpn-client curl http://httpbin.org/ip"
echo ""
echo "The key difference: server runs on HOST, client runs in namespace!"
