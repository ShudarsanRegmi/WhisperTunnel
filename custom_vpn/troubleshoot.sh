#!/bin/bash
echo "🔍 WhisperTunnel VPN Troubleshooting"
echo "===================================="

echo ""
echo "1. Checking VPN processes:"
echo "Server processes (should run on HOST):"
ps aux | grep "server\.py" | grep -v grep || echo "   ❌ No server process found"

echo ""
echo "Client processes (should run in vpn-client namespace):"
ps aux | grep "client\.py" | grep -v grep || echo "   ❌ No client process found"

echo ""
echo "2. Checking network interfaces:"
echo "Host TUN interfaces:"
ip addr show | grep -A 3 "tun" || echo "   ❌ No TUN interface on host"

echo ""
echo "Client namespace TUN interfaces:"
sudo ip netns exec vpn-client ip addr show | grep -A 3 "tun" 2>/dev/null || echo "   ❌ No TUN interface in client namespace"

echo ""
echo "3. Checking routing:"
echo "Client namespace routes:"
sudo ip netns exec vpn-client ip route show 2>/dev/null || echo "   ❌ Cannot access client namespace"

echo ""
echo "4. Checking DNS:"
echo "Client DNS config:"
sudo cat /etc/netns/vpn-client/resolv.conf 2>/dev/null || echo "   ❌ No DNS config found"

echo ""
echo "5. Testing basic connectivity:"
echo "VPN tunnel test (client -> server):"
if sudo ip netns exec vpn-client ping -c 1 10.8.0.1 >/dev/null 2>&1; then
    echo "   ✅ VPN tunnel works"
else
    echo "   ❌ VPN tunnel broken"
fi

echo ""
echo "📝 SOLUTION STEPS:"
echo "=================="
echo ""
echo "If server is not running on HOST:"
echo "   sudo python3 server/server.py --config config/server.json"
echo ""
echo "If client is not running in namespace:"
echo "   sudo ip netns exec vpn-client python3 client/client.py --config config/client.json"
echo ""
echo "If DNS is missing:"
echo "   sudo mkdir -p /etc/netns/vpn-client"
echo "   echo 'nameserver 8.8.8.8' | sudo tee /etc/netns/vpn-client/resolv.conf"
echo ""
echo "If no default route in client:"
echo "   sudo ip netns exec vpn-client ip route add default via 10.8.0.1 dev tun0"
