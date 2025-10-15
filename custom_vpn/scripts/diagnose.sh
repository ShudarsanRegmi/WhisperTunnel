#!/bin/bash
# STATUS: done
# Diagnostic script for WhisperTunnel VPN connectivity issues

set -e

CLIENT_NS="vpn-client"
SERVER_NS="vpn-server"
VPN_SUBNET="10.8.0.0/24"

echo "========================================"
echo "WhisperTunnel VPN Diagnostics"
echo "========================================"
echo ""

# Check if namespaces exist
echo "1. Checking network namespaces..."
if ip netns list | grep -q $CLIENT_NS; then
    echo "✅ Client namespace ($CLIENT_NS) exists"
else
    echo "❌ Client namespace ($CLIENT_NS) not found"
    echo "   Run: sudo bash scripts/netns_setup.sh"
    exit 1
fi

if ip netns list | grep -q $SERVER_NS; then
    echo "✅ Server namespace ($SERVER_NS) exists"
else
    echo "❌ Server namespace ($SERVER_NS) not found"
    echo "   Run: sudo bash scripts/netns_setup.sh"
    exit 1
fi

echo ""
echo "2. Checking TUN interfaces..."

# Check client TUN interface
if ip netns exec $CLIENT_NS ip addr show tun0 >/dev/null 2>&1; then
    echo "✅ Client TUN interface exists:"
    ip netns exec $CLIENT_NS ip addr show tun0 | grep -E "(inet|state)"
else
    echo "❌ Client TUN interface not found"
    echo "   Make sure client is running"
fi

# Check server TUN interface
if ip netns exec $SERVER_NS ip addr show tun0 >/dev/null 2>&1; then
    echo "✅ Server TUN interface exists:"
    ip netns exec $SERVER_NS ip addr show tun0 | grep -E "(inet|state)"
else
    echo "❌ Server TUN interface not found"
    echo "   Make sure server is running"
fi

echo ""
echo "3. Checking VPN tunnel connectivity..."
if ip netns exec $CLIENT_NS ping -c 2 10.8.0.1 >/dev/null 2>&1; then
    echo "✅ VPN tunnel is working (can ping server)"
else
    echo "❌ VPN tunnel not working (cannot ping server)"
    echo "   Make sure both client and server are running"
fi

echo ""
echo "4. Checking routing..."
echo "Client routes:"
ip netns exec $CLIENT_NS ip route show | head -5

echo ""
echo "Server routes:"
ip netns exec $SERVER_NS ip route show | head -5

echo ""
echo "5. Checking DNS configuration..."
if [ -f "/etc/netns/$CLIENT_NS/resolv.conf" ]; then
    echo "✅ DNS configured for client namespace:"
    cat /etc/netns/$CLIENT_NS/resolv.conf
else
    echo "❌ DNS not configured for client namespace"
    echo "   Run: sudo bash scripts/server_nat.sh"
fi

echo ""
echo "6. Checking IP forwarding..."
if [ "$(cat /proc/sys/net/ipv4/ip_forward)" = "1" ]; then
    echo "✅ IP forwarding is enabled"
else
    echo "❌ IP forwarding is disabled"
    echo "   Run: sudo sysctl -w net.ipv4.ip_forward=1"
fi

echo ""
echo "7. Checking iptables NAT rules..."
if iptables -t nat -L POSTROUTING -n | grep -q "$VPN_SUBNET"; then
    echo "✅ NAT rules are configured:"
    iptables -t nat -L POSTROUTING -n --line-numbers | grep "$VPN_SUBNET"
else
    echo "❌ NAT rules not found"
    echo "   Run: sudo bash scripts/server_nat.sh"
fi

echo ""
echo "8. Testing DNS resolution..."
if ip netns exec $CLIENT_NS nslookup google.com >/dev/null 2>&1; then
    echo "✅ DNS resolution works"
else
    echo "❌ DNS resolution fails"
    echo "   Check DNS configuration and network connectivity"
fi

echo ""
echo "9. Testing external connectivity..."
if ip netns exec $CLIENT_NS ping -c 2 8.8.8.8 >/dev/null 2>&1; then
    echo "✅ External IP connectivity works"
    if ip netns exec $CLIENT_NS curl -s --connect-timeout 5 http://httpbin.org/ip >/dev/null 2>&1; then
        echo "✅ HTTP connectivity works"
        echo "   Your external IP via VPN:"
        ip netns exec $CLIENT_NS curl -s --connect-timeout 10 http://httpbin.org/ip | grep -o '"origin": "[^"]*"' || echo "   Could not retrieve IP"
    else
        echo "⚠️  HTTP connectivity fails (but IP works)"
    fi
else
    echo "❌ External IP connectivity fails"
    echo "   Check NAT configuration and routing"
fi

echo ""
echo "10. Troubleshooting suggestions..."
echo ""

# Common issues and solutions
echo "If DNS resolution fails:"
echo "  - Ensure /etc/netns/$CLIENT_NS/resolv.conf exists with valid nameservers"
echo "  - Try: sudo bash scripts/server_nat.sh"
echo ""

echo "If external connectivity fails:"
echo "  - Check that both client and server VPN processes are running"
echo "  - Verify iptables rules: iptables -L FORWARD -n"
echo "  - Check default route in client: ip netns exec $CLIENT_NS ip route"
echo "  - Ensure VPN tunnel is working: ip netns exec $CLIENT_NS ping 10.8.0.1"
echo ""

echo "If HTTP fails but ping works:"
echo "  - Check firewall rules on the host system"
echo "  - Try different test URLs: curl -s http://example.com"
echo ""

echo "Manual tests you can try:"
echo "  sudo ip netns exec $CLIENT_NS ping 8.8.8.8"
echo "  sudo ip netns exec $CLIENT_NS nslookup google.com"
echo "  sudo ip netns exec $CLIENT_NS curl http://httpbin.org/ip"
echo "  sudo ip netns exec $CLIENT_NS traceroute 8.8.8.8"
