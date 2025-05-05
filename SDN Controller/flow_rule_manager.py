#!/usr/bin/env python3
# Flow Rule Manager - handles creation, sending and management of flow rules

import json
import logging
import time
import threading
from datetime import datetime
import os
import numpy as np

from config import *
from data_processor import df, tx_rx_mapping, current_interfaces, speed_data
from mqtt_handler import client

# Global variables for flow rule management
flow_rules = {}  # {node_id: {rule_num: rule}}
latest_flow_rules = []  # Track recent rules for reference
num_counter = 0  # Counter for generating rule numbers

def get_next_num():
    """Generate the next sequential rule number"""
    global num_counter
    num_counter += 1
    return f"{num_counter:03d}"

def send_flow_rule(node_id, latency_value, power_value, priority, current_interface):
    """
    Determine and send appropriate flow rules based on current interface
    """
    if current_interface == 'ITSG5':
        send_cv2x_flow_rules(node_id, latency_value, power_value, priority, 'Tech switching')
    elif current_interface == 'CV2X':
        send_itsg5_flow_rules(node_id, latency_value, power_value, priority, 'Tech switching')
    else:
        send_cv2x_flow_rules(node_id, latency_value, power_value, priority, 'Tech switching')
        send_itsg5_flow_rules(node_id, latency_value, power_value, priority, 'Tech switching')

def send_itsg5_flow_rules(rx_node_id, latency_value, power_value, priority, command_type):
    """
    Send ITSG5 flow rules to all nodes with appropriate roles
    """
    node_ids = get_all_node_ids()
    for node_id in node_ids:
        if node_id == rx_node_id:
            send_itsg5_flow_rule(node_id, 'ITSG5_rx', latency_value, power_value, priority, command_type)
        else:
            send_itsg5_flow_rule(node_id, 'ITSG5_tx', '*', '*', '*', command_type)
            tx_rx_mapping[node_id] = rx_node_id

def send_cv2x_flow_rules(rx_node_id, latency_value, power_value, priority, command_type):
    """
    Send CV2X flow rules to all nodes with appropriate roles
    """
    node_ids = get_all_node_ids()
    for node_id in node_ids:
        if node_id == rx_node_id:
            send_cv2x_flow_rule(node_id, 'CV2X_rx', latency_value, power_value, priority, command_type)
        else:
            send_cv2x_flow_rule(node_id, 'CV2X_tx', '*', '*', '*', command_type)
            tx_rx_mapping[node_id] = rx_node_id

def send_itsg5_flow_rule(node_id, action, latency_value, power_value, priority, command_type):
    """
    Create and send an ITSG5 flow rule
    """
    match = create_match_dict(node_id)
    timeout = calculate_timeout(node_id) if any(match[key] != '*' for key in match if key != 'NODE_ID') else 20
    
    flow_rule = {
        'Num': get_next_num(),
        'match': match,
        'Command type': command_type,
        'Value': action,
        'Rx Power Threshold': power_value,
        'Latency': latency_value,
        'Priority': priority,
        'Counter': 0,
        'Timeout': timeout
    }
    
    logging.info(f"Sending ITSG5 flow rule: {flow_rule}")
    publish_flow_rule(node_id, flow_rule)

def send_cv2x_flow_rule(node_id, action, latency_value, power_value, priority, command_type):
    """
    Create and send a CV2X flow rule
    """
    match = create_match_dict(node_id)
    timeout = calculate_timeout(node_id) if any(match[key] != '*' for key in match if key != 'NODE_ID') else 20
    
    flow_rule = {
        'Num': get_next_num(),
        'match': match,
        'Value': action,
        'Command type': command_type,
        'Rx Power Threshold': power_value,
        'Latency': latency_value,
        'Priority': priority,
        'Counter': 0,
        'Timeout': timeout
    }
    
    logging.info(f"Sending CV2X flow rule: {flow_rule}")
    publish_flow_rule(node_id, flow_rule)

def create_match_dict(node_id):
    """
    Create match dictionary for flow rule based on node's current data
    """
    return {
        'NODE_ID': node_id,
        'Src MAC': df.at[node_id, 'Src MAC'] if pd.notna(df.at[node_id, 'Src MAC']) else '*',
        'Des MAC': df.at[node_id, 'Des MAC'] if pd.notna(df.at[node_id, 'Des MAC']) else '*',
        'Src IP': df.at[node_id, 'Src IP'] if pd.notna(df.at[node_id, 'Src IP']) else '*',
        'Des IP': df.at[node_id, 'Des IP'] if pd.notna(df.at[node_id, 'Des IP']) else '*',
        'Src Port': df.at[node_id, 'Src Port'] if pd.notna(df.at[node_id, 'Src Port']) else '*',
        'Des Port': df.at[node_id, 'Des Port'] if pd.notna(df.at[node_id, 'Des Port']) else '*',
        'Current interface': df.at[node_id, 'Current interface'] if pd.notna(df.at[node_id, 'Current interface']) else '*'
    }

def calculate_timeout(node_id):
    """
    Calculate timeout based on node's speed and position
    """
    if node_id not in speed_data:
        return 20
    
    speed = speed_data[node_id]['speed']
    position = speed_data[node_id]['position']
    direction = speed_data[node_id]['direction']
    
    # Calculate time to coverage boundary
    if direction == 1:
        time_to_boundary = (COVERAGE - position) / (speed * 1000 / 3600)  # Convert speed to m/s
    else:
        time_to_boundary = position / (speed * 1000 / 3600)  # Convert speed to m/s
    
    # Cap timeout between 10 and 150 seconds
    return max(10, min(150, time_to_boundary))

def publish_flow_rule(node_id, flow_rule):
    """
    Publish flow rule to MQTT and store it locally
    """
    client.publish(f"{MQTT_TOPIC_COMMAND}/{node_id}", json.dumps(flow_rule), qos=1)
    store_flow_rule(node_id, flow_rule['Num'], flow_rule)

def store_flow_rule(node_id, num, flow_rule):
    """
    Store flow rule in local data structures and log file
    """
    global flow_rules, latest_flow_rules
    
    if node_id not in flow_rules:
        flow_rules[node_id] = {}
    flow_rules[node_id][num] = flow_rule
    
    # Keep track of recent rules
    latest_flow_rules.append({'NODE_ID': node_id, 'Value': flow_rule['Value']})
    if len(latest_flow_rules) > 3:
        latest_flow_rules.pop(0)
    
    # Log the rule
    with open(FLOWRULE_LOG, 'a') as f:
        f.write(json.dumps(flow_rule) + '\n')

def flow_rule_exists(node_id, value):
    """
    Check if a flow rule with given value exists for a node
    """
    if node_id in flow_rules:
        for rule in flow_rules[node_id].values():
            if rule["Value"] == value:
                return True
    return False

def get_latest_interface():
    """
    Get the latest interface from recent flow rules
    """
    if not latest_flow_rules:
        return None
    
    latest_rule = latest_flow_rules[-1]
    if 'ITSG5' in latest_rule['Value']:
        return 'ITSG5'
    elif 'CV2X' in latest_rule['Value']:
        return 'CV2X'
    return None

def send_forwarding_rule(node_id, next_hop, forwarding_interface, value_type):
    """
    Create and send a forwarding flow rule
    """
    next_hop_mac = df.at[next_hop, 'Src MAC'] if next_hop in df.index and pd.notna(df.at[next_hop, 'Src MAC']) else '*'
    
    # Check if rule already exists
    existing_rules = flow_rules.get(node_id, {})
    for rule in existing_rules.values():
        if rule['Command type'] == 'Forwarding' and rule['Next hop'] == next_hop_mac:
            return
    
    # Create new forwarding rule
    num = get_next_num()
    flow_rule = {
        'Num': num,
        'match': create_match_dict(node_id),
        'Command type': 'Forwarding',
        'Value': value_type,
        'Next hop': next_hop_mac,
        'Rx Power Threshold': '*',
        'Latency': '*',
        'Priority': '*',
        'Counter': 0,
        'Timeout': 20
    }
    
    logging.info(f"Sending Forwarding Rule: {flow_rule}")
    publish_flow_rule(node_id, flow_rule)

def send_execution_message_to_tx(rx_node_id, rx_current_interface):
    """
    Send execution message to TX node when RX interface changes
    """
    tx_node_id = [k for k, v in tx_rx_mapping.items() if v == rx_node_id]
    if not tx_node_id:
        return
    
    tx_node_id = tx_node_id[0]
    if rx_current_interface == 'ITSG5':
        value = 'ITSG5_tx'
    elif rx_current_interface == 'CV2X':
        value = 'CV2X_tx'
    else:
        return
    
    message = {
        'NODE_ID': tx_node_id,
        'Value': value
    }
    
    logging.info(f"Sending execution message to tx NODE: {message}")
    client.publish(f"{MQTT_TOPIC_COMMAND}/{tx_node_id}", json.dumps(message), qos=1)
    with open(FLOWRULE_LOG, 'a') as f:
        f.write(json.dumps(message) + '\n')

def get_all_node_ids():
    """Get list of all node IDs from data processor"""
    from data_processor import get_all_node_ids
    return get_all_node_ids()
