#!/usr/bin/env python3
# MQTT Client Handler - manages all MQTT communication and callbacks

import json
import logging
import paho.mqtt.client as mqtt
from datetime import datetime
import time
import threading
import pandas as pd
import os

from config import *
from data_processor import process_received_data, handle_disabled_flow_rule
from flow_rule_manager import send_initialization_flow_rule

# Initialize logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s')

# Global variables needed for MQTT operations
client = None
T_r = None
T_s = None
T_g = None
T_b = None

def initialize_mqtt_client():
    """Initialize and configure the MQTT client"""
    global client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MTT_PORT, 60)
    return client

def on_connect(client, userdata, flags, rc):
    """Callback when connection to MQTT broker is established"""
    logging.info(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC_DATA, qos=1)
    client.subscribe(MQTT_TOPIC_DISABLE, qos=1)
    client.subscribe(MQTT_TOPIC_RECEIVED, qos=1)
    logging.info(f"Subscribed to {MQTT_TOPIC_DATA} and {MQTT_TOPIC_DISABLE}")

def on_message(client, userdata, msg):
    """
    Callback when message is received from MQTT broker
    Handles different message types and routes them appropriately
    """
    global T_r, T_s, T_g, T_b
    
    logging.debug(f"Received raw message on topic {msg.topic}: {msg.payload}")
    
    try:
        data = json.loads(msg.payload)
        logging.info(f"Processed message on topic {msg.topic}: {data}")
        
        # Log received data
        with open(RECEIVED_DATA_LOG, 'a') as f:
            f.write(json.dumps(data) + '\n')
        
        # Route message based on topic
        if msg.topic == MQTT_TOPIC_DISABLE:
            handle_disabled_flow_rule(data)
            return
            
        if msg.topic == MQTT_TOPIC_RECEIVED:
            handle_received_message(data)
            return
            
        if 'NODE_ID' in data:
            process_received_data(data, msg.topic)
            
    except Exception as e:
        logging.error(f"Error processing message: {e}")

def handle_received_message(data):
    """
    Special handling for received messages (acknowledgements)
    Calculates and logs timing metrics
    """
    global T_r, T_s, T_g, T_b
    
    T_b = time.time()
    data["Timestamp"] = T_b
    
    with open(RECEIVED_MESSAGE_LOG, 'a') as f:
        f.write(json.dumps(data) + '\n')

    if all(t is not None for t in [T_r, T_s, T_g, T_b]):
        calculate_and_log_timing_metrics()

def calculate_and_log_timing_metrics():
    """
    Calculate timing metrics between different stages
    and log them to the testing data file
    """
    global T_r, T_s, T_g, T_b
    
    controller_delay = T_s - T_r
    time_to_generate = T_s - T_g
    time_to_send_fl = (T_b - T_s) / 2

    current_interface = get_current_interface()
    opposite_interface = get_opposite_interface(current_interface)

    with open(TESTING_DATA_LOG, 'a') as f:
        f.write(f"Controller_Dealy from {current_interface} to {opposite_interface}: {controller_delay * 1000} milliseconds\n")
        f.write(f"Time_to_generate from {current_interface} to {opposite_interface}: {time_to_generate * 1000} milliseconds\n")
        f.write(f"Time_to_send_FL from {current_interface} to {opposite_interface}: {time_to_send_fl * 1000} milliseconds\n")

    # Reset timing variables
    T_r = T_s = T_g = T_b = None

def get_current_interface():
    """Determine current interface based on flow rules"""
    # Implementation depends on flow_rule_manager module
    from flow_rule_manager import get_latest_interface
    return get_latest_interface()

def get_opposite_interface(current_interface):
    """Get the opposite interface of the given one"""
    if current_interface == "ITSG5":
        return "CV2X"
    elif current_interface == "CV2X":
        return "ITSG5"
    return "Unknown"

def start_mqtt_loop():
    """Start the MQTT network loop"""
    global client
    client.loop_start()

def stop_mqtt_loop():
    """Stop the MQTT network loop"""
    global client
    client.loop_stop()
