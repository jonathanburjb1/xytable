# Network Setup for Mesa 7I96S Board

This document describes how to set up the network connection between the Raspberry Pi and the Mesa 7I96S board.

## Overview

The Mesa 7I96S board is configured with a static IP address of `192.168.1.121`. To communicate with it, the Raspberry Pi's ethernet interface needs to be configured on the same subnet.

## Current Configuration

- **Mesa Board IP**: `192.168.1.121`
- **Raspberry Pi Ethernet IP**: `192.168.1.100/24`
- **Subnet**: `192.168.1.0/24`
- **Gateway**: `192.168.1.1`

## Network Setup

### Automatic Setup

Use the provided script to configure the network:

```bash
# Set up the connection
./scripts/network_setup.sh setup

# Check status
./scripts/network_setup.sh status

# Test connectivity
./scripts/network_setup.sh test
```

### Manual Setup

If you prefer to configure manually:

1. **Configure NetworkManager connection**:
   ```bash
   sudo nmcli connection modify "Wired connection 1" \
       ipv4.method manual \
       ipv4.addresses 192.168.1.100/24 \
       ipv4.gateway 192.168.1.1
   ```

2. **Activate the connection**:
   ```bash
   sudo nmcli connection up "Wired connection 1"
   ```

3. **Verify the configuration**:
   ```bash
   ip addr show eth0
   ip route show
   ping -c 3 192.168.1.121
   ```

## Verification

### Check Network Status

```bash
# Show ethernet interface configuration
ip addr show eth0

# Show routing table
ip route show

# Test connectivity to Mesa board
ping -c 3 192.168.1.121
```

### Test Mesa Driver

```bash
# Test Mesa board connection through the driver
python3 -m src.cli.main mesa test-connection
```

## Troubleshooting

### Cannot Ping Mesa Board

1. **Check physical connection**: Ensure the ethernet cable is connected between the Pi and Mesa board
2. **Check Mesa board power**: Ensure the Mesa board is powered on
3. **Check Mesa board IP**: Verify the Mesa board is configured with IP `192.168.1.121`
4. **Check network configuration**: Run `./scripts/network_setup.sh status`

### Network Configuration Issues

1. **Reset to DHCP**: If you need to reset the connection:
   ```bash
   ./scripts/network_setup.sh reset
   ```

2. **Check NetworkManager logs**:
   ```bash
   journalctl -u NetworkManager -f
   ```

3. **Restart NetworkManager**:
   ```bash
   sudo systemctl restart NetworkManager
   ```

### LinuxCNC Connection Issues

If the Mesa driver shows "simulation mode":

1. **Ensure LinuxCNC is running**:
   ```bash
   # Start LinuxCNC with the Mesa configuration
   linuxcnc config/linuxcnc/mesa_7i96s/mesa_7i96s.ini
   ```

2. **Check LinuxCNC HAL configuration**:
   - Verify `config/linuxcnc/mesa_7i96s/mesa_7i96s.hal` contains the correct IP
   - Ensure the hostmot2 driver is loaded correctly

## Persistence

The network configuration is persistent and will survive reboots. The configuration is stored in NetworkManager and will automatically apply when the ethernet interface is connected.

## Script Commands

The `scripts/network_setup.sh` script provides the following commands:

- `setup`: Configure ethernet for Mesa board connection
- `status`: Show current network status
- `test`: Test connectivity to Mesa board
- `reset`: Reset connection to DHCP mode

## Configuration Files

- **Network Configuration**: Managed by NetworkManager
- **Mesa Driver Config**: `config/settings.yaml`
- **LinuxCNC HAL Config**: `config/linuxcnc/mesa_7i96s/mesa_7i96s.hal`
- **LinuxCNC INI Config**: `config/linuxcnc/mesa_7i96s/mesa_7i96s.ini` 