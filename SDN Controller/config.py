#!/usr/bin/env python3
# Configuration module - contains all constants and paths

import os
from datetime import datetime

# MQTT Configuration
MQTT_BROKER = '172.16.0.1'
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = 'node/command'
MQTT_TOPIC_DATA = 'node/data/#'
MQTT_TOPIC_DISABLE = 'node/disable'
MQTT_TOPIC_RECEIVED = 'node/received'

# Logging Configuration
LOG_PATH = '/home/ferromobile/srsRAN_4G/test/Qoc_log'
RECEIVED_DATA_LOG = os.path.join(LOG_PATH, 'received_data.log')
CALCULATION_LATENCY_LOG = os.path.join(LOG_PATH, 'calculation_latency.log')
CALCULATION_POWER_LOG = os.path.join(LOG_PATH, 'calculation_power.log')
FLOWRULE_LOG = os.path.join(LOG_PATH, 'flowrule.log')
DISABLE_FLOWRULE_LOG = os.path.join(LOG_PATH, 'disable_flowrule.log')
REALTIME_RULE_LOG = os.path.join(LOG_PATH, 'realtime_rule.log')
TESTING_DATA_LOG = os.path.join(LOG_PATH, 'Testing_Data_CV2X_SNR30_Speed10.log')
RECEIVED_MESSAGE_LOG = os.path.join(LOG_PATH, 'Received_message.log')

# Data Structure Configuration
BASE_COLUMNS = ['NODE_ID', 'Current interface', 'Speed']
OPTIONAL_COLUMNS = [
    'Src MAC', 'Des MAC', 'Src IP', 'Des IP', 'Src Port', 'Des Port',
    'Freq', 'Power', 'Noise', 'RSSI', 'CBR', 'DataRate', 'Latency',
    'PCR', 'PER', 'PPS', 'CBP', 'Position', 'Payload', 'Timestamp'
]

# Network Configuration
COVERAGE = 2000  # in meters
DEFAULT_SPEED = 40  # km/h
