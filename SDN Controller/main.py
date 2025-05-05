#!/usr/bin/env python3
# Main Application - ties all modules together and manages execution

import os
import time
import threading
from mqtt_handler import initialize_mqtt_client, start_mqtt_loop
from node_manager import start_node_management_threads
from metrics_monitor import monitor_metrics

def initialize_application():
    """Initialize all application components"""
    # Set up MQTT client
    client = initialize_mqtt_client()
    
    # Start management threads
    start_node_management_threads()
    
    # Start metrics monitoring in background
    threading.Thread(target=monitor_metrics, daemon=True).start()
    
    # Start MQTT loop
    start_mqtt_loop()
    
    return client

def main():
    """Main application entry point"""
    # Clear console and initialize
    os.system('clear')
    client = initialize_application()
    
    # Main command loop
    try:
        while True:
            command = input("Enter command (itsg5n/cv2xn): ").strip().lower()
            handle_user_command(command)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        client.disconnect()

def handle_user_command(command):
    """Process user input commands"""
    from data_processor import get_all_node_ids
    from flow_rule_manager import (
        send_itsg5_flow_rule,
        send_cv2x_flow_rule
    )
    
    if command not in ['itsg5n', 'cv2xn']:
        print("Invalid command. Use 'itsg5n' or 'cv2xn'")
        return
    
    node_ids = get_all_node_ids()
    if len(node_ids) < 2:
        print("Error: Not enough nodes have sent data yet.")
        return
    
    tx_node, rx_node = node_ids[0], node_ids[1]
    
    if command == 'itsg5n':
        send_itsg5_flow_rule(tx_node, 'ITSG5_tx', '*', '*', '*', 'Tech switching')
        send_itsg5_flow_rule(rx_node, 'ITSG5_rx', '*', '*', '*', 'Tech switching')
    elif command == 'cv2xn':
        send_cv2x_flow_rule(tx_node, 'CV2X_tx', '*', '*', '*', 'Tech switching')
        send_cv2x_flow_rule(rx_node, 'CV2X_rx', '*', '*', '*', 'Tech switching')

if __name__ == "__main__":
    main()
