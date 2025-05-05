#!/usr/bin/env python3
# Node Manager - handles node movement simulation and state tracking

import time
import threading
import logging
from datetime import datetime
import os
import pandas as pd

from config import *

def simulate_node_movement():
    """
    Continuously simulate node movement within coverage area
    Updates position and direction for all nodes
    """
    while True:
        update_node_positions()
        time.sleep(1)  # Update every second

def update_node_positions():
    """
    Update position and direction for all nodes based on their speed
    """
    from data_processor import speed_data
    
    for node_id in list(speed_data.keys()):
        speed = speed_data[node_id]['speed']
        position = speed_data[node_id]['position']
        direction = speed_data[node_id]['direction']
        
        # Calculate new position (speed in km/h converted to m/s)
        new_position = position + direction * (speed * 1000 / 3600)
        
        # Reverse direction if boundary reached
        if new_position >= COVERAGE or new_position <= 0:
            speed_data[node_id]['direction'] *= -1
            new_position = max(0, min(COVERAGE, new_position))
        
        speed_data[node_id]['position'] = new_position
        
        # Log position update
        logging.debug(f"Node {node_id} moved to position {new_position:.2f}m "
                     f"(speed: {speed}km/h, direction: {'+' if direction > 0 else '-'})")

def log_realtime_rules():
    """
    Continuously log current flow rules to file
    """
    from flow_rule_manager import flow_rules
    
    while True:
        with open(REALTIME_RULE_LOG, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Current Flow Rules:\n")
            for node_id, rules in flow_rules.items():
                f.write(f"  Node {node_id}:\n")
                for rule_num, rule in rules.items():
                    f.write(f"    {rule_num}: {rule}\n")
            f.write("\n")
        time.sleep(10)

def initialize_node(node_id, initial_speed=DEFAULT_SPEED):
    """
    Initialize a new node with default movement parameters
    """
    from data_processor import speed_data
    
    speed_data[node_id] = {
        'speed': initial_speed,
        'position': 0,  # Starting position in meters
        'direction': 1   # 1 for moving forward, -1 for backward
    }
    logging.info(f"Initialized node {node_id} with speed {initial_speed} km/h")

def get_node_position(node_id):
    """
    Get current position of a node
    """
    from data_processor import speed_data
    return speed_data.get(node_id, {}).get('position', 0)

def get_node_speed(node_id):
    """
    Get current speed of a node
    """
    from data_processor import speed_data
    return speed_data.get(node_id, {}).get('speed', DEFAULT_SPEED)

def set_node_speed(node_id, new_speed):
    """
    Update speed for a specific node
    """
    from data_processor import speed_data
    if node_id in speed_data:
        speed_data[node_id]['speed'] = new_speed
        logging.info(f"Updated node {node_id} speed to {new_speed} km/h")
    else:
        logging.warning(f"Attempted to set speed for unknown node {node_id}")

def reverse_node_direction(node_id):
    """
    Reverse movement direction for a specific node
    """
    from data_processor import speed_data
    if node_id in speed_data:
        speed_data[node_id]['direction'] *= -1
        logging.info(f"Reversed direction for node {node_id}")
    else:
        logging.warning(f"Attempted to reverse direction for unknown node {node_id}")

def start_node_management_threads():
    """
    Start all node management related threads
    """
    threading.Thread(target=simulate_node_movement, daemon=True).start()
    threading.Thread(target=log_realtime_rules, daemon=True).start()
    logging.info("Started node management threads")
