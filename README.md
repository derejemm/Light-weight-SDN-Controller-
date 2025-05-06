# Light-weight-SDN-Controller-
A light-weight SDN controller designed for an integrated road-rail networks.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Linux](https://img.shields.io/badge/platform-Linux-critical.svg)](https://kernel.org)
[![OS](https://img.shields.io/badge/platform-Linux-orange.svg)](https://www.kernel.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

This repository implements a Software-Defined Networking (SDN) framework for managing multi-interface V2X (Vehicle-to-Everything) communication nodes. It supports dynamic interface switching between ITS-G5 and CV2X, and ensures link resilience through a multi-hop fallback mechanism.

## Table of Contents

- [Overview](#overview)
- [Components](#components)
- [Dependencies](#dependencies)
- [Usage](#usage)
- [Logs](#logs)
- [Getting Started](#Getting_Started)

---

## Overview

The system consists of:
- A centralized **SDN Controller** (`controller.py`) that distributes flow rules via MQTT.
- Distributed **SDN-Enabled Nodes** (`obu/rsu.py`) that dynamically switch between wireless technologies and report telemetry.
- A **fallback forwarding mechanism** using Wi-Fi Direct for resilient communication when primary interfaces fail.
- A **Switching Mudule** intergrated in Nodes devices to manage the switching between varies interfaces.

---

## Components

### 1. `controller.py`
- Subscribes to data topics from each node (`node/data/NODE_ID`).
- Publishes flow rules via `node/command/NODE_ID`.
- Decides interface switching or multihop logic based on latency, power, and packet loss.
- Detects failures and assigns new forwarding paths.
- Manage the disturbed flow rules(eg. Enabled/Expired)

### 2. `node_client.py`
- Subscribes to flow rules via MQTT and evaluates matching criteria.
- Measures delay, power, PER from ITS-G5/CV2X interfaces, extract data from diffrent interfaces and send to the controller.
- Executes interface switching using `switch_tech.py`.
- In `GO` or `Client` mode, runs Wi-Fi Direct scripts to maintain connectivity.

### 3. `switch_tech.py`
- Command-line script to:
  - Start/stop ITS-G5 or CV2X transmission/reception.
  - Disconnect current technology.
  - Check active technology.

### 4. `wifi_p2p_server.py` (GO)
- Discovers target client MAC.
- Establishes P2P group.
- Assigns static IP `192.168.49.1`.
- Starts TCP listener on port `9000`.

### 5. `wifi_p2p_client.py` (Client)
- Discovers and connects to target GO.
- Assigns static IP `192.168.49.2`.
- Verifies connectivity before data forwarding.

---

## Dependencies—Software

### SDN Controller: 
[![MQTT](https://img.shields.io/badge/protocol-MQTT-green.svg)](https://mqtt.org/)
[![srsRAN 4G/5G](https://img.shields.io/badge/network-srsRAN-orange.svg)](https://github.com/srsRAN/srsRAN_Project)
[![Open5GS](https://img.shields.io/badge/core%20network-Open5GS-yellow.svg)](https://open5gs.org/)

### SDN Enabled Nodes:
[![Wi‑Fi Direct](https://img.shields.io/badge/connectivity-WiFi--Direct-9cf.svg)](https://en.wikipedia.org/wiki/Wi-Fi_Direct)
[![wpa_supplicant](https://img.shields.io/badge/tool-wpa__supplicant-important.svg)](https://w1.fi/wpa_supplicant/)
[![netcat](https://img.shields.io/badge/tool-netcat-lightgrey.svg)](https://linux.die.net/man/1/nc)
[![iproute2](https://img.shields.io/badge/tool-iproute2-lightgrey.svg)](https://wiki.linuxfoundation.org/networking/iproute2)

### Testing:

#### The test flow table is sent from the controller to the node and configured in the enb/gnb.conf file for the communication environment.
[![srsRAN 4G/5G](https://img.shields.io/badge/network-srsRAN-orange.svg)](https://github.com/srsRAN/srsRAN_Project)
[![Open5GS](https://img.shields.io/badge/core%20network-Open5GS-yellow.svg)](https://open5gs.org/)

#### The ITG5/CV2X test section can be configured using the LLC and ACME tools included with MK6 devices to send data. GNURadio is used to configure the communication environment.
[![ITSG5 Tool](https://img.shields.io/badge/module-llc-lightgrey.svg)]([https://www.nordsys.de/](https://support.cohdawireless.com/))
[![C-V2X Tool](https://img.shields.io/badge/module-acme-lightgrey.svg)]([https://www.qualcomm.com/](https://support.cohdawireless.com/))
[![GNU Radio](https://img.shields.io/badge/SDR-GNU%20Radio-orange.svg)](https://www.gnuradio.org/)

#### The testing part of the multi-hop network requires the use of commonly used network tools.
[![netcat](https://img.shields.io/badge/tool-netcat-lightgrey.svg)](https://linux.die.net/man/1/nc)
[![iperf](https://img.shields.io/badge/tool-iperf-lightgrey.svg)](https://iperf.fr/)
[![iproute2](https://img.shields.io/badge/tool-iproute2-lightgrey.svg)](https://wiki.linuxfoundation.org/networking/iproute2)
[![ifconfig](https://img.shields.io/badge/tool-ifconfig-lightgrey.svg)](https://man7.org/linux/man-pages/man8/ifconfig.8.html)

## Dependencies—Hardware

### MK6 series devices(RSU/OBU)
This project runs on Cohda Wireless MK6 series devices (including OBU and RSU), supporting native ITS-G5 (IEEE 802.11p) and C-V2X communication. It integrates dedicated modules such as llc, etsa, and acme for low-level channel control and data acquisition. The device supports enabling Wi-Fi Direct via wpa_supplicant and can be remotely accessed via SSH. All modules and drivers are available through the Cohda Wireless official support platform(https://www.cohdawireless.com/).

### USRP-2901
USRP devices used for base station support in srsRAN and for channel modulation support between MK6 devices.

###
Usage

1. Base Station & Core Network Setup
Ensure the core LTE/5G infrastructure is running to enable communication between the SDN Controller and Nodes.

Step 1: Configure user_db.csv
In srsRAN's EPC configuration, ensure each node's IMSI, key, and APN are registered:

```csv
imsi,key,opc,amf,msisdn
001010123456789,00112233445566778899aabbccddeeff,00000000000000000000000000000000,8000,0000000001
```

Step 2: Start srsRAN and Open5GS
```bash
# EPC (srsRAN)
sudo srsran_epc

# eNB (srsRAN)
sudo srsran_enb

# 5G Core (Open5GS)
sudo systemctl start open5gs-mmed
sudo systemctl start open5gs-sgwcd
sudo systemctl start open5gs-sgwud

```

You may need to configure:

enb.conf (to match eNB IP and MME)

gnb.conf (for 5G testbed if applicable)

2. Run the SDN Controller
```bash
python3 controller.py
```
The controller subscribes to telemetry (node/data/NODE_ID) and dispatches flow rules (node/command/NODE_ID) via MQTT.

3. Deploy Nodes
On each SDN-enabled node (e.g., MK6 OBU/RSU):
```bash
python3 obu/rsu.py
```
Each node will:

Initialize with a unique NODE_ID

Report metrics from its interface (ITS-G5 or CV2X)

Apply flow rules sent from the controller

Automatically switch communication tech as needed

4. Run Interface Switching Script
Each node automatically uses switch_tech.py during control events. You can also manually invoke it:
```bash
python3 switch_tech.py ITSG5_tx      # Start ITS-G5 TX
python3 switch_tech.py CV2X_rx       # Start CV2X RX
python3 switch_tech.py disc          # Disconnect all
python3 switch_tech.py check         # Check current interface
```
5. Configure and Use Wi-Fi Direct Fallback
Used when both ITS-G5 and CV2X fail.

On GO (Group Owner):
```bash
python3 wifi_p2p_server.py <CLIENT_MAC>
Assigns IP 192.168.49.1
```
Listens on port 9000 for forwarded packets

On Client:
```bash
python3 wifi_p2p_client.py <GO_MAC>
Assigns IP 192.168.49.2
```

Connects to GO via MAC discovery and P2P handshake

## Logs

All log files are stored in `/mnt/rw/log/` on the MK6 device unless otherwise specified. They help track the node status, performance metrics, switching events, and forwarding behavior.

| Log File | Description |
|----------|-------------|
| `Data_Testing.log` | Timestamped records of interface switching durations and events. |
| `extracted_data.log` | Real-time telemetry from interfaces (RSSI, latency, PER, power, etc.). |
| `match_info.log` | Last known match parameters for flow rule matching (e.g., MAC, IP). |
| `real_time_rules.log` | Stores a copy of all currently received flow rules from the controller. |
| `executed_flow_value.log` | Tracks the latest executed value (e.g., ITSG5_tx, CV2X_rx, GO, etc.) along with a timestamp. |
| `Forwarding_info.log` | Captures data received through Wi-Fi Direct socket on the GO node. |
| `llc_tx_test.log`, `llc_rx_test.log` | Output of ITS-G5 traffic generation tools (e.g., LLC test-tx/rx). |
| `llc_rssi_tx.log`, `llc_rssi_rx.log` | Channel quality and RSSI reports from ITS-G5 logs. |
| `cv2x_tx.log`, `cv2x_rx.log` | Packet traces of CV2X communication captured via `tcpdump`. |
| `acme_rx.log` | Output of C-V2X ACME reception logs, including latency, PPS, CBP. |
| `Testing_Data` | Time-stamped switching info between interfaces with durations. |

> ⚠️ Note: These logs are crucial for evaluating switching delays, connectivity stability, and flow rule effectiveness. They are used in analysis and visualization tools for post-processing.

## Getting_Started

You can clone or download this repository using the following command:

```bash
git clone https://github.com/derejemm/Light-weight-SDN-Controller-.git





