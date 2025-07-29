#!/bin/bash
# Mesa Board Network Setup Script
# This script helps manage the network connection to the Mesa 7I96S board

set -e

MESA_IP="192.168.1.121"
PI_IP="192.168.1.100"
CONNECTION_NAME="Wired connection 1"
INTERFACE="eth0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check general internet connectivity
check_internet_connectivity() {
    print_status $BLUE "Checking general internet connectivity..."
    if ping -c 3 -W 5 8.8.8.8 >/dev/null 2>&1; then
        print_status $GREEN "✓ Internet connectivity is good (8.8.8.8 responds)"
        return 0
    else
        print_status $YELLOW "⚠ Warning: No internet connectivity (8.8.8.8 not responding)"
        return 1
    fi
}

# Function to check if interface exists
check_interface() {
    if ! ip link show "$INTERFACE" >/dev/null 2>&1; then
        print_status $RED "✗ Error: Interface $INTERFACE does not exist"
        return 1
    fi
    return 0
}

# Function to check if connection exists
check_connection() {
    if ! nmcli connection show "$CONNECTION_NAME" >/dev/null 2>&1; then
        print_status $RED "✗ Error: Connection '$CONNECTION_NAME' does not exist"
        print_status $BLUE "Available connections:"
        nmcli connection show | grep -v "NAME\|lo" | awk '{print "  " $1}'
        return 1
    fi
    return 0
}

# Function to get current IP of interface
get_interface_ip() {
    ip addr show "$INTERFACE" | grep -oP 'inet \K\S+' | head -1
}

# Function to test Mesa board connectivity
test_mesa_connectivity() {
    print_status $BLUE "Testing connectivity to Mesa board at $MESA_IP..."
    if ping -c 3 -W 5 "$MESA_IP" >/dev/null 2>&1; then
        print_status $GREEN "✓ Mesa board is reachable at $MESA_IP"
        return 0
    else
        print_status $YELLOW "⚠ Warning: Cannot reach Mesa board at $MESA_IP"
        print_status $BLUE "  Please check:"
        print_status $BLUE "  - Mesa board is powered on"
        print_status $BLUE "  - Ethernet cable is connected"
        print_status $BLUE "  - Mesa board IP is configured to $MESA_IP"
        return 1
    fi
}

echo "Mesa Board Network Setup"
echo "======================="

case "$1" in
    "setup")
        print_status $BLUE "Setting up network connection to Mesa board..."
        
        # Check prerequisites
        if ! check_interface; then
            exit 1
        fi
        
        if ! check_connection; then
            exit 1
        fi
        
        # Check current internet connectivity
        check_internet_connectivity
        
        # Get current IP
        CURRENT_IP=$(get_interface_ip)
        print_status $BLUE "Current IP on $INTERFACE: $CURRENT_IP"
        
        # Only configure if IP is different
        if [ "$CURRENT_IP" != "$PI_IP" ]; then
            print_status $BLUE "Configuring $CONNECTION_NAME with IP $PI_IP/24 (no gateway)..."
            
            # Configure the connection
            if ! sudo nmcli connection modify "$CONNECTION_NAME" \
                ipv4.method manual \
                ipv4.addresses "$PI_IP/24" \
                ipv4.gateway "" \
                ipv4.dns ""; then
                print_status $RED "✗ Failed to configure connection"
                exit 1
            fi
            
            print_status $BLUE "Activating connection..."
            if ! sudo nmcli connection up "$CONNECTION_NAME"; then
                print_status $RED "✗ Failed to activate connection"
                exit 1
            fi
            
            # Wait for connection to stabilize
            sleep 3
            
            # Verify new IP
            NEW_IP=$(get_interface_ip)
            if [ "$NEW_IP" = "$PI_IP" ]; then
                print_status $GREEN "✓ Successfully configured IP to $PI_IP"
            else
                print_status $YELLOW "⚠ Warning: IP configuration may not have taken effect"
                print_status $BLUE "  Expected: $PI_IP, Got: $NEW_IP"
            fi
        else
            print_status $GREEN "✓ IP already configured correctly ($PI_IP)"
        fi
        
        # Add static route for Mesa board (if not already present)
        if ! ip route show | grep -q "$MESA_IP/32"; then
            print_status $BLUE "Adding static route for Mesa board..."
            if sudo ip route add "$MESA_IP/32" dev "$INTERFACE" 2>/dev/null; then
                print_status $GREEN "✓ Static route added"
            else
                print_status $YELLOW "⚠ Route may already exist or failed to add"
            fi
        else
            print_status $GREEN "✓ Static route already exists"
        fi
        
        # Test Mesa board connectivity
        test_mesa_connectivity
        
        # Final connectivity check
        print_status $BLUE "Final connectivity summary:"
        check_internet_connectivity
        test_mesa_connectivity
        ;;
    
    "status")
        print_status $BLUE "Network Status:"
        echo "==============="
        
        # Check interface
        if check_interface; then
            print_status $BLUE "Ethernet Interface ($INTERFACE):"
            ip addr show "$INTERFACE" | grep -E "(inet|state)" || true
        fi
        
        echo ""
        print_status $BLUE "Routes to Mesa board:"
        ip route show | grep "192.168.1" || print_status $YELLOW "  No routes found to 192.168.1.x"
        
        echo ""
        # Test connectivity
        check_internet_connectivity
        test_mesa_connectivity
        ;;
    
    "test")
        print_status $BLUE "Testing Mesa board connection..."
        
        # Check general connectivity first
        check_internet_connectivity
        
        # Test Mesa board specifically
        if ping -c 3 -W 5 "$MESA_IP" >/dev/null 2>&1; then
            print_status $GREEN "✓ Mesa board is responding to ping"
            print_status $BLUE "Ping results:"
            ping -c 3 "$MESA_IP"
        else
            print_status $RED "✗ Mesa board is not responding"
            print_status $BLUE "Detailed ping attempt:"
            ping -c 3 "$MESA_IP" || true
        fi
        ;;
    
    "reset")
        print_status $BLUE "Resetting network connection..."
        
        if ! check_connection; then
            exit 1
        fi
        
        print_status $BLUE "Bringing down connection..."
        sudo nmcli connection down "$CONNECTION_NAME" || true
        
        print_status $BLUE "Resetting to DHCP mode..."
        if sudo nmcli connection modify "$CONNECTION_NAME" ipv4.method auto; then
            print_status $GREEN "✓ Connection reset to DHCP mode"
        else
            print_status $RED "✗ Failed to reset connection"
            exit 1
        fi
        
        print_status $BLUE "Bringing up connection..."
        if sudo nmcli connection up "$CONNECTION_NAME"; then
            print_status $GREEN "✓ Connection activated"
        else
            print_status $RED "✗ Failed to activate connection"
            exit 1
        fi
        
        # Wait for DHCP
        sleep 5
        
        # Show new status
        print_status $BLUE "New network status:"
        ip addr show "$INTERFACE" | grep -E "(inet|state)" || true
        ;;
    
    "check")
        print_status $BLUE "Running comprehensive network check..."
        echo ""
        
        # Check interface
        if check_interface; then
            print_status $GREEN "✓ Interface $INTERFACE exists"
        fi
        
        # Check connection
        if check_connection; then
            print_status $GREEN "✓ Connection '$CONNECTION_NAME' exists"
        fi
        
        # Check internet connectivity
        check_internet_connectivity
        
        # Check Mesa connectivity
        test_mesa_connectivity
        
        # Show current configuration
        echo ""
        print_status $BLUE "Current network configuration:"
        CURRENT_IP=$(get_interface_ip)
        print_status $BLUE "  Interface: $INTERFACE"
        print_status $BLUE "  Current IP: $CURRENT_IP"
        print_status $BLUE "  Expected IP: $PI_IP"
        print_status $BLUE "  Mesa IP: $MESA_IP"
        ;;
    
    *)
        echo "Usage: $0 {setup|status|test|reset|check}"
        echo ""
        echo "Commands:"
        echo "  setup   - Configure ethernet for Mesa board connection"
        echo "  status  - Show current network status"
        echo "  test    - Test connectivity to Mesa board"
        echo "  reset   - Reset connection to DHCP mode"
        echo "  check   - Run comprehensive network check"
        echo ""
        echo "Configuration:"
        echo "  Mesa board IP: $MESA_IP"
        echo "  Raspberry Pi ethernet IP: $PI_IP"
        echo "  Interface: $INTERFACE"
        echo "  Connection: $CONNECTION_NAME"
        exit 1
        ;;
esac 
