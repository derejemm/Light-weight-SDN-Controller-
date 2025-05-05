#!/usr/bin/env python3
# Node Configuration - Centralized settings for the node implementation

import os
import random
import string

# MQTT Configuration
MQTT_BROKER = '172.16.0.1'
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = 'node/command'
MQTT_TOPIC_DATA = 'node/data'
MQTT_TOPIC_DISABLE = 'node/disable'
MQTT_TOPIC_RECEIVED = 'node/received'

# Node Identity
NODE_ID = ''.join(random.choices(string.digits, k=2)) + ''.join(random.choices(string.ascii_letters, k=2))
NODE_INFO = {'NODE_ID': NODE_ID, 'Speed': 40}

# Logging Paths
LOG_BASE = '/mnt/rw/log'
EXTRACTED_DATA_LOG = f'{LOG_BASE}/extracted_data.log'
MATCH_INFO_LOG = f'{LOG_BASE}/match_info.log'
REAL_TIME_RULES_LOG = f'{LOG_BASE}/real_time_rules.log'
EXECUTED_FLOW_VALUE_LOG = f'{LOG_BASE}/executed_flow_value.log'

# Interface Configuration
CV2X_IFACES = {'tx': 'rmnet_usb1', 'rx': 'rmnet_usb1'}

# External Script Paths
SWITCH_SCRIPT = '/mnt/rw/switch_tech.py'
WIFI_CLIENT_SCRIPT = '/mnt/rw/wifi_p2p_client.py'
WIFI_SERVER_SCRIPT = '/mnt/rw/wifi_p2p_server.py'

# Forwarding Configuration
FORWARDING_SOCKET_ADDR = ("192.168.49.1", 9000)
FORWARDING_TIMEOUT = 10

# Threshold Defaults
LATENCY_THRESHOLD = float('inf')
POWER_THRESHOLD = float('inf')
