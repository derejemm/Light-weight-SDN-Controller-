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
- [License](#license)

---

## Overview

The system consists of:
- A centralized **SDN Controller** (`controller.py`) that distributes flow rules via MQTT.
- Distributed **SDN-Enabled Nodes** (`node_client.py`) that dynamically switch between wireless technologies and report telemetry.
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


```bash
pip install -r requirements.txt




