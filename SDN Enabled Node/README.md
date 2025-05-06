# SDN-Enabled Vehicular Node

[![MQTT Client](https://img.shields.io/badge/client-paho--mqtt-orange.svg)](https://pypi.org/project/paho-mqtt/)
[![wpa_supplicant](https://img.shields.io/badge/tool-wpa__supplicant-important.svg)](https://w1.fi/wpa_supplicant/)
[![netcat](https://img.shields.io/badge/tool-netcat-lightgrey.svg)](https://linux.die.net/man/1/nc)

## Overview
Real-time communication node supporting dynamic interface switching (CV2X/ITS-G5) and multi-hop forwarding via SDN control. Acts as both endpoint and relay in vehicular networks.

## Key Features
- Dual-mode operation: CV2X and ITS-G5 interfaces
- SDN control: Flow rule processing from controller
- QoS monitoring: Latency/power threshold detection
- Multi-hop forwarding: Wi-Fi Direct fallback paths
- Real-time data extract: PER, CBR, PPS metrics

## Repository Structure
```text
main.py
├── mqtt_handler.py
├── flow_rule_processor.py
├── tech_controller.py
│   ├── data_monitor.py
│   └── forwarding_manager.py
└── config.py
```

## Testing Part
The series of T_* parameters for testing, such as the time taken of switching module.

# SDN Node Core Logic Flows

## 1. Main Control Flow
```text
Y → MQTT message received?
  │
  ├─ Y → Contains flow rule?
  │      │
  │      ├─ Y → Rule NODE_ID matches this node?
  │      │      │
  │      │      ├─ Y → Is Initialization rule?
  │      │      │      │
  │      │      │      ├─ Y → Execute initialization ∧ Send ACK
  │      │      │      │
  │      │      │      └─ N → Evaluate thresholds ∧ Update counter
  │      │      │
  │      │      └─ N → Discard rule
  │      │
  │      └─ N → Contains execution command?
  │             │
  │             ├─ Y → Execute run_value()
  │             │
  │             └─ N → Log unknown message
  │
  └─ N → Check connection ∧ Reconnect
```

## 2. Rule Execution Flow (run_value)
```text
Y → Is technology switch command? (ITSG5/CV2X)
  │
  ├─ Y → Stop current captures → Start new interface → Send 3x interface status
  │      │
  │      ├─ ITSG5 mode? → ifconfig up ∧ Start llc capture
  │      │
  │      └─ CV2X mode? → Start tcpdump ∧ Configure rmnet
  │
  └─ N → Is forwarding command? (C/GO)
         │
         ├─ Y → Get next-hop MAC → Start Wi-Fi Direct
         │      │
         │      ├─ Client mode? → Delay 10s startup
         │      │
         │      └─ Group Owner? → Immediate start
         │
         └─ N → Log unknown command
```

## 3. Data Monitoring Flow
```text
Y → Extraction interval reached?
  │
  ├─ Y → Read second-newest log line → Parse metrics
  │      │
  │      ├─ Threshold exceeded?
  │      │      │
  │      │      ├─ Y → Trigger rule re-evaluation
  │      │      │
  │      │      └─ N → Normal report to controller
  │      │
  │      └─ Forwarding mode active?
  │             │
  │             ├─ Y → Forward via Socket
  │             │
  │             └─ N → MQTT report only
  │
  └─ N → Continue monitoring cycle
```

## 4. Exception Handling Flow
```text
Y → Zero-value metric detected? (latency=0/power=0)
  │
  ├─ Y → Zero-count++ → Exceeds 10?
  │      │
  │      ├─ Y → Trigger fallback rule
  │      │
  │      └─ N → Continue monitoring
  │
  └─ N → 3+ consecutive threshold violations?
         │
         ├─ Y → Priority-based rule switch
         │
         └─ N → Maintain current state
```

## 5. Forwarding Engine Flow
```text
Y → Data received for forwarding?
  │
  ├─ Y → Socket connected?
  │      │
  │      ├─ Y → Immediate send ∧ Update queue
  │      │
  │      └─ N → Start retry (5 attempts/3s interval)
  │
  └─ N → Check queue backlog → Retry after 1s timeout
```

## Key Decision Parameters
1. Technology Switch Conditions:
   - Latency threshold: 20-30ms (configurable)
   - Power threshold: -75dBm (configurable)

2. Forwarding Triggers:
   - Valid next-hop MAC
   - Wi-Fi Direct pairing successful
   - Socket connection established

3. Exception Conditions:
   - 3+ consecutive threshold violations
   - 10+ zero-value readings
   - Interface unresponsive (5s timeout)
