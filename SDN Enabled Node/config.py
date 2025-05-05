#!/usr/bin/env python3
# Node Configuration - Core parameters and paths

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

# Log Paths
LOG_BASE = '/mnt/rw/log'
EXTRACTED_DATA_LOG = f'{LOG_BASE}/extracted_data.log'
MATCH_INFO_LOG = f'{LOG_BASE}/match_info.log'
REAL_TIME_RULES_LOG = f'{LOG_BASE}/real_time_rules.log'
EXECUTED_FLOW_VALUE_LOG = f'{LOG_BASE}/executed_flow_value.log'

# Interface Logs
LLC_RSSI_TX_LOG = f'{LOG_BASE}/llc_rssi_tx.log'
LLC_RSSI_RX_LOG = f'{LOG_BASE}/llc_rssi_rx.log'
LLC_CBR_LOG = f'{LOG_BASE}/llc_cbr.log'
LLC_TX_TEST_LOG = f'{LOG_BASE}/llc_tx_test.log'
LLC_RX_TEST_LOG = f'{LOG_BASE}/llc_rx_test.log'
CV2X_TX_LOG = f'{LOG_BASE}/cv2x_tx.log'
CV2X_RX_LOG = f'{LOG_BASE}/cv2x_rx.log'
ACME_RX_LOG = f'{LOG_BASE}/acme_lan/acme_rx.log'

# Interface Configuration
CV2X_IFACES = {'tx': 'rmnet_usb1', 'rx': 'rmnet_usb1'}
