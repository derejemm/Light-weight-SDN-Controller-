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

## Dependencies

### Python
Install with:

```bash
pip install -r requirements.txt




