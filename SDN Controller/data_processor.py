#!/usr/bin/env python3
# Data Processing Module - manages DataFrame and processes incoming node data

import pandas as pd
import numpy as np
import logging
import time
import threading
import json
from datetime import datetime
import os

from config import *

# Initialize global data structures
df = pd.DataFrame(columns=BASE_COLUMNS + OPTIONAL_COLUMNS)
active_nodes = {}
switching_nodes = set()
received_nodes = []
latency_data = {}
power_data = {}
current_interfaces = {}
tx_rx_mapping = {}
speed_data = {}  # Store speed and position data
calculate_metrics = True

def process_received_data(data, topic):
    """
    Process incoming data from nodes and update data structures
    """
    global df, calculate_metrics, received_nodes, latency_data, power_data
    
    node_id = data['NODE_ID']
    current_interface = data.get('Current interface', '*')
    speed = data.get('Speed', DEFAULT_SPEED)
    
    # Update active nodes
    active_nodes[node_id] = data
    
    # Initialize node data if not present
    if node_id not in received_nodes:
        received_nodes.append(node_id)
        initialize_node_data(node_id, current_interface, speed)
    
    # Update DataFrame with new data
    update_dataframe(node_id, data)
    
    # Handle interface changes
    if 'Current interface' in data:
        handle_interface_change(node_id, current_interface, speed)
    
    # Process metrics data
    process_metrics_data(node_id, data)
    
    # Display updated data
    display_node_data()

def initialize_node_data(node_id, current_interface, speed):
    """
    Initialize data structures for a new node
    """
    global df, speed_data
    
    # Send initialization flow rule
    from flow_rule_manager import send_initialization_flow_rule
    send_initialization_flow_rule(node_id)
    
    # Add new row to DataFrame
    new_row = pd.Series({col: None for col in df.columns}, name=node_id)
    new_row['NODE_ID'] = node_id
    new_row['Current interface'] = current_interface
    new_row['Speed'] = speed
    df = df._append(new_row)
    
    # Initialize speed tracking
    speed_data[node_id] = {
        'speed': speed,
        'position': 0,
        'direction': 1  # 1 for forward, -1 for backward
    }

def update_dataframe(node_id, data):
    """
    Update DataFrame with new data from node
    """
    global df
    
    for key, value in data.items():
        if key in df.columns:
            df.at[node_id, key] = value

def handle_interface_change(node_id, current_interface, speed):
    """
    Handle node interface changes and trigger related actions
    """
    global df, current_interfaces, calculate_metrics
    
    previous_interface = df.at[node_id, 'Current interface']
    df.at[node_id, 'Current interface'] = current_interface
    df.at[node_id, 'Speed'] = speed
    
    if current_interface != previous_interface:
        current_interfaces[node_id] = current_interface
        clear_node_parameters(node_id)
        
        # Handle execution message for TX nodes
        if node_id in tx_rx_mapping.values():
            from flow_rule_manager import send_execution_message_to_tx
            send_execution_message_to_tx(node_id, current_interface)

def clear_node_parameters(node_id):
    """
    Clear metrics data and schedule parameter clearing
    """
    global latency_data, power_data, calculate_metrics
    
    # Clear immediately
    clear_latency_and_power_data(node_id)
    
    # Schedule future clearing
    for i in range(1, 6):
        threading.Timer(i, clear_latency_and_power_data, [node_id]).start()
    
    threading.Timer(6, partial_clear_node_parameters, [node_id]).start()
    
    calculate_metrics = False
    threading.Timer(10, restart_metrics_calculation).start()

def clear_latency_and_power_data(node_id):
    """
    Clear latency and power data for a specific node
    """
    global latency_data, power_data
    latency_data[node_id] = []
    power_data[node_id] = []
    logging.info(f"Cleared latency and power data for NODE_ID: {node_id}")

def partial_clear_node_parameters(node_id):
    """
    Clear optional parameters for a node after delay
    """
    global df
    df.loc[node_id, OPTIONAL_COLUMNS] = None
    logging.info(f"Cleared parameters for NODE_ID: {node_id} after delay")

def restart_metrics_calculation():
    """
    Re-enable metrics calculation after delay
    """
    global calculate_metrics
    calculate_metrics = True
    logging.info("Restarted metrics calculation after delay")

def process_metrics_data(node_id, data):
    """
    Process and store latency and power metrics
    """
    global latency_data, power_data
    
    # Process latency data
    if 'Latency' in data:
        if node_id not in latency_data:
            latency_data[node_id] = []
        latency_value = float(data['Latency'].replace('ms', ''))
        latency_data[node_id].append(latency_value)
        if len(latency_data[node_id]) > 5:
            latency_data[node_id].pop(0)
    
    # Process power data
    if 'Power' in data:
        power_value = float(data['Power'].split(',')[1])
        if power_value < 1000:  # Sanity check
            if node_id not in power_data:
                power_data[node_id] = []
            power_data[node_id].append(power_value)
            if len(power_data[node_id]) > 5:
                power_data[node_id].pop(0)

def display_node_data():
    """
    Display current node data in console
    """
    global df
    display_df = df.dropna(axis=1, how='all')
    os.system('clear')
    for node_id in display_df.index:
        print(f"NODE_ID: {node_id}")
        node_df = display_df.loc[[node_id]].dropna(axis=1, how='all')
        print(node_df.to_string(index=False))
        print('\n')

def get_node_data(node_id):
    """
    Get data for specific node
    """
    global df
    return df.loc[node_id] if node_id in df.index else None

def get_all_node_ids():
    """
    Get list of all known node IDs
    """
    global df
    return list(df.index.values)
