# SDN Controller with CV2X/ITS-G5 Interface Switching and Multi-Hop Forwarding

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MQTT Broker](https://img.shields.io/badge/broker-mosquitto-blue.svg)](https://mosquitto.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Python-based controller for managing interface switching and multi-hop forwarding in vehicular networks, using MQTT for real-time communication.

## Project Structure

```text
├── config.py             # Configuration and constants
├── data_processor.py     # Node state tracking
├── flow_rule_manager.py  # Rule generation (including forwarding)
├── metrics_monitor.py    # Failure detection & relay selection
├── mqtt_handler.py       # Communication layer
├── node_manager.py       # Mobility simulation
└── main.py               # Entry point
```


## Key Features

### 1. Dual-Mode Flow Rules
- Switching Rules: Manage interface transitions between CV2X and ITS-G5
- Forwarding Rules: Enable multi-hop communication for fault tolerance

### 2. Core Capabilities
- Real-time QoS monitoring (latency/power)
- Dynamic interface switching
- Relay node selection for failed nodes
- Movement-aware timeout calculation
- Comprehensive logging system

## Flow Rule Types

| Rule Type        | Purpose                          | Trigger Condition                     |
|------------------|----------------------------------|---------------------------------------|
| `Tech switching` | Interface transition             | QoS threshold violation               |
| `Forwarding`     | Multi-hop packet relay           | Node failure/coverage gap detection  |
| `Initialization` | Node setup/reset                 | New node registration                 |

**Switching Rule Example**:
{
  "Num": "012",
  "Command type": "Tech Switching",
  "Value": "ITSG5",  // Switch to ITS_G5
  "Next hop": "aa:bb:cc:dd:ee:ff",
  "Current interface": "CV2X",
  "Timeout": 45  // Movement-aware duration
}

**Forwarding Rule Example**:
{
  "Num": "012",
  "Command type": "Forwarding",
  "Value": "GO",  // Group Owner role
  "Next hop": "aa:bb:cc:dd:ee:ff",
  "Current interface": "CV2X",
  "Timeout": 45  // Movement-aware duration
}

## Testing Part
The series of T_* parameters for testing, such as the robustness of SDN Controller(Self delay), the time of flow rules reach Nodes,etc.

# SDN Controller Core Logic Flows

## 1. Node Registration Flow
Y → New MQTT connection established?
  │
  ├─ Y → Contains NODE_ID and capabilities?
  │      │
  │      ├─ Y → Add to node registry ∧ Send INIT rule
  │      │      │
  │      │      └─ Start topology timer (20s)
  │      │
  │      └─ N → Send error ∧ Close connection
  │
  └─ N → Continue listening

## 2. Flow Rule Decision Flow
Y → Received node metrics update?
  │
  ├─ Y → Metrics show threshold violation?
  │      │
  │      ├─ Y → Latency or Power violation?
  │      │      │
  │      │      ├─ Latency → Calculate new ITSG5/CV2X priority
  │      │      │      │
  │      │      │      └─ Generate switching rules (5x retry)
  │      │      │
  │      │      └─ Power → Check RSSI ∧ Update threshold rules
  │      │
  │      └─ N → Log normal status
  │
  └─ N → Check for stale nodes (30s timeout)

## 3. Switching Logic Flow
Y → Need interface switch?
  │
  ├─ Y → Single node or pair affected?
  │      │
  │      ├─ Single → Send direct tech-switch rule
  │      │      │
  │      │      └─ Start T_r timer
  │      │
  │      └─ Pair → Coordinate TX/RX rules
  │             │
  │             ├─ Calculate switching sequence
  │             │
  │             └─ Enforce timing sync (T_g, T_s)
  │
  └─ N → Check for forwarding needs

## 4. Forwarding Path Flow
Y → Abnormal node detected?
  │
  ├─ Y → Available relay node?
  │      │
  │      ├─ Y → Create forwarding rules:
  │      │      │
  │      │      ├─ C rule for receiver (192.168.49.1)
  │      │      │
  │      │      └─ GO rule for relay
  │      │
  │      └─ N → Trigger alert ∧ Disable node
  │
  └─ N → Monitor path stability

## 5. Rule Timeout Flow
Y → Rule expiration time reached?
  │
  ├─ Y → Rule still valid?
  │      │
  │      ├─ Y → Renew with new timeout
  │      │      │
  │      │      └─ Update priority
  │      │
  │      └─ N → Send DISABLE command
  │             │
  │             └─ Cleanup flow tables
  │
  └─ N → Continue monitoring

## Key Timing Parameters
1. Switching Sequence:
   - T_r: Rule receive timestamp
   - T_g: Rule generation delay (<50ms)
   - T_s: Rule send timestamp
   - T_b: Node ACK received

2. Thresholds:
   - Latency critical: >30ms (5 samples)
   - Power critical: < -80dBm (3 samples)
   - Zero-value timeout: 10 samples

3. Forwarding:
   - Relay selection time: <200ms
   - Socket timeout: 5s
   - Retry interval: 3s

## Failure Handling
Y → Node unresponsive?
  │
  ├─ Y → Attempt rediscovery (3x)
  │      │
  │      ├─ Successful?
  │      │      │
  │      │      ├─ Y → Re-sync state
  │      │      │
  │      │      └─ N → Mark offline
  │      │
  │      └─ Update topology
  │
  └─ N → Check rule compliance

## Tool Version
paho-mqtt==1.6.1
pandas==2.2.2
numpy==1.26.4
