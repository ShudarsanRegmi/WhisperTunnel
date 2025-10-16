#!/bin/bash
echo "🔧 Setting up VPN routing for internet traffic..."

# Check if TUN interface exists
if ! ip addr show tun0 >/dev/null 2>&1; then
    echo "❌ TUN interface not found. Make sure VPN client is running."
    exit 1
fi

# Get current default route info
DEFAULT_GW=$(ip route show default | awk '{print $3}' | head -1)
DEFAULT_IF=$(ip route show default | awk '{print $5}' | head -1)

echo "📋 Current setup:"
echo "  Default gateway: $DEFAULT_GW"
echo "  Default interface: $DEFAULT_IF"
echo "  VPN server: 35.225.48.199"

# Add route for VPN server through original gateway (to avoid routing loop)
echo "🛣️  Adding route for VPN server..."
sudo ip route add 35.225.48.199/32 via $DEFAULT_GW dev $DEFAULT_IF

# Add route for local network (to keep local access)
echo "🏠 Adding route for local network..."
LOCAL_NET=$(ip route show | grep $DEFAULT_IF | grep -E '192\.168\.|10\.|172\.' | head -1 | awk '{print $1}')
if [ ! -z "$LOCAL_NET" ]; then
    sudo ip route add $LOCAL_NET via $DEFAULT_GW dev $DEFAULT_IF 2>/dev/null || true
fi

# Change default route to use VPN tunnel
echo "🌐 Changing default route to VPN tunnel..."
sudo ip route del default
sudo ip route add default via 10.8.0.1 dev tun0

echo ""
echo "✅ VPN routing configured!"
echo ""
echo "🧪 Testing setup:"

# Test VPN tunnel
echo -n "VPN tunnel: "
if ping -c 1 10.8.0.1 >/dev/null 2>&1; then
    echo "✅ Working"
else
    echo "❌ Failed"
fi

# Test internet via VPN
echo -n "Internet via VPN: "
if curl -s --connect-timeout 5 http://httpbin.org/ip >/dev/null 2>&1; then
    echo "✅ Working"
    echo ""
    echo "🎉 Your public IP should now be: 35.225.48.199"
    curl -s http://httpbin.org/ip
else
    echo "❌ Failed"
fi

echo ""
echo "📝 Current routes:"
ip route show | head -10
