# Wi-Fi Direct Forwarding Module

## Overview

This module enables peer-to-peer (P2P) Wi-Fi Direct connectivity for multi-hop vehicular communication. It acts as a backup forwarding path when primary interfaces like CV2X or ITSG5 are impaired or unavailable. The system is designed to work under an SDN-based control plane, which assigns roles (GO or Client) dynamically via flow rules.

## Components

### 1. Group Owner (GO)
**File**: `wifi_p2p_server.py`  
Behavior:
- Initializes P2P Wi-Fi Direct group
- Starts peer discovery and connects to target client
- Creates P2P interface (e.g., `p2p-wlan0-0`)
- Assigns IP `192.168.49.1`
- Opens TCP listener on port `9000`
- Forwards incoming data to `/mnt/rw/log/Forwarding_info.log`

### 2. Client
**File**: `wifi_p2p_client.py`  
Behavior:
- Discovers target GO device via MAC
- Connects using P2P and configures new interface
- Assigns static IP `192.168.49.2`
- Pings GO until reachable
- Sends socket data to GO on port `9000`

## Key Features

- **60-second MAC-based peer discovery**
- **Manual IP assignment**, avoiding DHCP delays
- **Ping-based GO reachability verification**
- **Socket-based data forwarding (TCP/9000)**
- **Robust retry logic for interface creation**
- **Real-time logging to** `/mnt/rw/log/Forwarding_info.log`

--------------------------------------------------------------------------

# Required Linux Tools
- wpa_supplicant (with nl80211 backend)
- wpa_cli
- netcat (nc)

## Required Configuration

### `wpa_supplicant` Configuration File

Create file:  
`/etc/wpa_supplicant/p2p.conf`

```conf
ctrl_interface=/var/run/wpa_supplicant   # Specifies the control interface directory for wpa_supplicant
update_config=1                         # Allows wpa_cli to modify the configuration file
device_name=RSU_DEVICE                  # Device name displayed when discovered by other devices
device_type=1-0050F204-1                 # Wi-Fi Direct device type code
config_methods=display push_button keypad  # Allows display, push-button (PBC), and keypad (PIN) pairing methods
p2p_go_intent=15                         # Forces RSU to be the Wi-Fi Direct Group Owner (GO)


