#!/usr/bin/env python3
# Metrics Monitor - handles monitoring, analysis, and switching decisions

import numpy as np
import logging
import time
import threading
from datetime import datetime
from functools import partial

from config import *
from data_processor import latency_data, power_data, switching_nodes, received_nodes
from flow_rule_manager import (
    send_flow_rule, 
    send_initialization_flow_rule,
    send_itsg5_flow_rule,
    send_cv2x_flow_rule,
    send_forwarding_rule,
    flow_rule_exists
)

def monitor_metrics():
    """
    Continuously monitor metrics and trigger analysis when needed
    """
    last_latency_data = {}
    last_power_data = {}
    
    while True:
        time.sleep(5)
        check_node_metrics(last_latency_data, last_power_data)

def check_node_metrics(last_latency_data, last_power_data):
    """
    Check metrics for all nodes and trigger analysis if data changed
    """
    for node_id in list(latency_data.keys()):
        if (len(latency_data.get(node_id, [])) == 5 and 
            latency_data.get(node_id) != last_latency_data.get(node_id)):
            last_latency_data[node_id] = list(latency_data[node_id])
            analyze_node_metrics(node_id)
            
    for node_id in list(power_data.keys()):
        if (len(power_data.get(node_id, [])) == 5 and 
            power_data.get(node_id) != last_power_data.get(node_id)):
            last_power_data[node_id] = list(power_data[node_id])
            analyze_node_metrics(node_id)

def analyze_node_metrics(node_id):
    """
    Analyze metrics for a specific node and make switching decisions
    """
    # Calculate averages and standard deviations
    avg_latency, std_latency = calculate_latency_stats(node_id)
    avg_power, std_power = calculate_power_stats(node_id)
    
    # Check if metrics indicate need for switching
    if should_switch_interface(avg_latency, std_latency, avg_power, std_power):
        trigger_interface_switch(node_id, avg_latency, std_latency, avg_power, std_power)
    elif is_abnormal_metrics(avg_latency, avg_power):
        handle_abnormal_metrics(node_id)

def calculate_latency_stats(node_id):
    """
    Calculate latency statistics for a node
    """
    if node_id in latency_data and len(latency_data[node_id]) == 5:
        avg = np.mean(latency_data[node_id])
        std = np.std(latency_data[node_id])
        
        logging.info(f"Average latency for NODE {node_id}: {avg} ms, Std: {std} ms")
        with open(CALCULATION_LATENCY_LOG, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - NODE_ID: {node_id} - "
                   f"Average Latency: {avg} ms, Std: {std} ms\n")
        return avg, std
    return None, None

def calculate_power_stats(node_id):
    """
    Calculate power statistics for a node
    """
    if node_id in power_data and len(power_data[node_id]) == 5:
        avg = np.mean(power_data[node_id])
        std = np.std(power_data[node_id])
        
        logging.info(f"Average power for NODE {node_id}: {avg} dBm, Std: {std} dBm")
        with open(CALCULATION_POWER_LOG, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - NODE_ID: {node_id} - "
                   f"Average Power: {avg} dBm, Std: {std} dBm\n")
        return avg, std
    return None, None

def should_switch_interface(avg_latency, std_latency, avg_power, std_power):
    """
    Determine if interface should be switched based on metrics
    """
    latency_condition = (avg_latency is not None and 
                         20.0 <= avg_latency <= 60000)
    power_condition = (avg_power is not None and 
                       -100 <= avg_power <= -75)
    
    return latency_condition or power_condition

def is_abnormal_metrics(avg_latency, avg_power):
    """
    Check if metrics are abnormal (out of expected ranges)
    """
    latency_abnormal = (avg_latency is not None and 
                        (avg_latency > 60000 or avg_latency <= 0 or np.isnan(avg_latency)))
    power_abnormal = (avg_power is not None and 
                      (avg_power < -100 or avg_power == 0 or np.isnan(avg_power)))
    
    return latency_abnormal or power_abnormal

def trigger_interface_switch(node_id, avg_latency, std_latency, avg_power, std_power):
    """
    Trigger interface switching based on metrics
    """
    if avg_latency is not None:
        trigger_type = 'latency'
        priority = '1,0'
    else:
        trigger_type = 'power'
        priority = '0,1'
    
    handle_switching(node_id, trigger_type, avg_latency, std_latency, 
                     avg_power, std_power, priority)

def handle_switching(node_id, trigger_type, avg_latency, std_latency, 
                    avg_power, std_power, priority):
    """
    Handle the interface switching process
    """
    from data_processor import current_interfaces
    
    current_interface = current_interfaces.get(node_id)
    
    # Calculate adjusted values based on metrics
    if trigger_type == 'latency':
        if avg_latency + 2 * std_latency < 30:
            latency_value = avg_latency + 2 * std_latency
        else:
            latency_value = 30.0
        power_value = np.interp(avg_power, [-45, -10], [-70, -45])
    else:  # power trigger
        if avg_power - 2 * std_power > -80:
            power_value = avg_power - 2 * std_power
        else:
            power_value = -80.0
        latency_value = np.interp(avg_latency, [5, 20], [20, 25])
    
    # Send appropriate flow rules
    if not flow_rules.get(node_id):
        send_flow_rule(node_id, latency_value, power_value, priority, current_interface)
    else:
        itsg5_exists = any(rule['Value'].startswith('ITSG5') for rule in flow_rules[node_id].values())
        cv2x_exists = any(rule['Value'].startswith('CV2X') for rule in flow_rules[node_id].values())
        
        if not (itsg5_exists and cv2x_exists):
            if cv2x_exists and current_interface == 'CV2X':
                send_flow_rule(node_id, latency_value, power_value, priority, 'CV2X')
            elif itsg5_exists and current_interface == 'ITSG5':
                send_flow_rule(node_id, latency_value, power_value, priority, 'ITSG5')

def handle_abnormal_metrics(node_id):
    """
    Handle cases where metrics are abnormal (out of range)
    """
    if len(received_nodes) < 3:
        logging.warning("Not enough nodes for forwarding, skipping.")
        return
    
    third_node = received_nodes[2]
    if third_node in switching_nodes:
        logging.info(f"Skipping switching for {third_node}, already in progress.")
        return
    
    # Find abnormal RX node from latest flow rules
    abnormal_rx_node = None
    switch_value = None
    for rule in reversed(latest_flow_rules):
        if "rx" in rule["Value"]:
            abnormal_rx_node = rule["NODE_ID"]
            switch_value = rule["Value"]
            break
    
    if not abnormal_rx_node:
        logging.warning("No rx node found, aborting flow modification.")
        return
    
    logging.info(f"Abnormal rx node found: {abnormal_rx_node}, sending initialization flow rule.")
    
    # Reset abnormal node
    if not flow_rule_exists(abnormal_rx_node, "Initialization"):
        send_initialization_flow_rule(abnormal_rx_node)
    
    # Configure third node as backup
    if not flow_rule_exists(third_node, switch_value):
        logging.info(f"Sending switching flow rule to third node {third_node} with Value: {switch_value}")
        
        if "ITSG5" in switch_value:
            send_itsg5_flow_rule(third_node, switch_value, '*', '*', '*', 'Tech switching')
        elif "CV2X" in switch_value:
            send_cv2x_flow_rule(third_node, switch_value, '*', '*', '*', 'Tech switching')
        
        switching_nodes.add(third_node)
        threading.Thread(target=wait_for_interface_update, 
                        args=(third_node, abnormal_rx_node)).start()

def wait_for_interface_update(third_node, rx_node):
    """
    Wait for interface update and complete the switching process
    """
    from data_processor import df, latency_data, power_data
    
    target_interface = df.at[rx_node, 'Current interface'] if rx_node in df.index else '*'
    
    while True:
        time.sleep(1)
        if df.at[third_node, 'Current interface'] == target_interface:
            complete_switching_process(third_node, rx_node, target_interface)
            break

def complete_switching_process(third_node, rx_node, target_interface):
    """
    Complete the switching process after interface update
    """
    from data_processor import switching_nodes, received_nodes
    
    # Send forwarding rules
    send_forwarding_rule(third_node, rx_node, target_interface, "C")
    
    # Clean up data
    latency_data.clear()
    power_data.clear()
    logging.info("Cleared latency_data and power_data after sending CLIENT.")
    
    # Update node tracking
    if third_node in switching_nodes:
        switching_nodes.remove(third_node)
    received_nodes[2] = rx_node
    
    # Wait for MAC address before sending GO rule
    while True:
        time.sleep(1)
        if third_node in df.index and pd.notna(df.at[third_node, "Src MAC"]):
            send_forwarding_rule(rx_node, third_node, target_interface, "GO")
            break
