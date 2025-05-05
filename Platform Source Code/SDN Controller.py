#!/usr/bin/env python3

import logging
import paho.mqtt.client as mqtt
import json
import pandas as pd
import os
from datetime import datetime, timedelta
import time
import threading
import numpy as np

# Configuration
MQTT_BROKER = '172.16.0.1'
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = 'node/command'
MQTT_TOPIC_DATA = 'node/data/#'
MQTT_TOPIC_DISABLE = 'node/disable'
MQTT_TOPIC_RECEIVED = 'node/received'
LOG_PATH = '/home/ferromobile/srsRAN_4G/test/Qoc_log'
RECEIVED_DATA_LOG = os.path.join(LOG_PATH, 'received_data.log')
CALCULATION_LATENCY_LOG = os.path.join(LOG_PATH, 'calculation_latency.log')
CALCULATION_POWER_LOG = os.path.join(LOG_PATH, 'calculation_power.log')
FLOWRULE_LOG = os.path.join(LOG_PATH, 'flowrule.log')
DISABLE_FLOWRULE_LOG = os.path.join(LOG_PATH, 'disable_flowrule.log')
REALTIME_RULE_LOG = os.path.join(LOG_PATH, 'realtime_rule.log')
TESTING_DATA_LOG = os.path.join(LOG_PATH, 'Testing_Data_CV2X_SNR30_Speed10.log')
RECEIVED_MESSAGE_LOG = os.path.join(LOG_PATH, 'Received_message.log') 

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s')

# Initialize DataFrame
base_columns = ['NODE_ID', 'Current interface', 'Speed']
optional_columns = ['Src MAC', 'Des MAC', 'Src IP', 'Des IP', 'Src Port', 'Des Port', 'Freq', 'Power', 'Noise', 'RSSI',
                    'CBR', 'DataRate', 'Latency', 'PCR', 'PER', 'PPS', 'CBP', 'Position', 'Payload', 'Timestamp']
df = pd.DataFrame(columns=base_columns + optional_columns)

active_nodes = {}
switching_nodes = set()
latest_flow_rules = []
received_nodes = []
latency_data = {}
power_data = {}
current_interfaces = {}
flow_rules = {}
num_counter = 0
tx_rx_mapping = {}
calculate_metrics = True
last_latency_data = {}
last_power_data = {}
last_interface = None

# Initialize time variables
T_r = None
T_s = None
T_g = None
T_b = None

# Coverage and speed
COVERAGE = 2000  # in meters
speed_data = {}  # Store speed and position data


def get_next_num():
    global num_counter
    num_counter += 1
    return f"{num_counter:03d}"


def on_connect(client, userdata, flags, rc):
    logging.info(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC_DATA, qos=1)
    client.subscribe(MQTT_TOPIC_DISABLE, qos=1)
    client.subscribe(MQTT_TOPIC_RECEIVED, qos=1)
    logging.info(f"Subscribed to {MQTT_TOPIC_DATA} and {MQTT_TOPIC_DISABLE}")


def on_message(client, userdata, msg):
    global df, flow_rules, tx_rx_mapping, calculate_metrics, last_latency_data, last_power_data, speed_data, last_interface
    global T_r, T_s, T_g, T_b
    logging.debug(f"Received raw message on topic {msg.topic}: {msg.payload}")
    try:
        data = json.loads(msg.payload)
        logging.info(f"Processed message on topic {msg.topic}: {data}")
        with open(RECEIVED_DATA_LOG, 'a') as f:
            f.write(json.dumps(data) + '\n')
        if 'NODE_ID' in data:
            node_id = data['NODE_ID']
            active_nodes[node_id] = data  

        if msg.topic == MQTT_TOPIC_DISABLE:
            handle_disabled_flow_rule(data)
            return

        if msg.topic == MQTT_TOPIC_RECEIVED:
            T_b = time.time()
            data["Timestamp"] = T_b
            with open(RECEIVED_MESSAGE_LOG, 'a') as f:
                f.write(json.dumps(data) + '\n')

            if T_r and T_s and T_g and T_b:
                Controller_Dealy = T_s - T_r
                time_to_generate = T_s - T_g
                time_to_send_fl = (T_b - T_s) / 2

                if last_interface is None:
                    current_interface = "Unknown"
                    opposite_interface = "Unknown"
                    if flow_rules:
                        latest_rule = next(iter(flow_rules.values()))
                        if latest_rule:
                            latest_rule_data = next(iter(latest_rule.values()))
                            current_interface = latest_rule_data.get('match', {}).get('Current interface', 'Unknown')
                            if current_interface == 'ITSG5':
                                opposite_interface = 'CV2X'
                            elif current_interface == 'CV2X':
                                opposite_interface = 'ITSG5'
                else:
                    if last_interface == "ITSG5":
                        current_interface = "CV2X"
                        opposite_interface = "ITSG5"
                    else:
                        current_interface = "ITSG5"
                        opposite_interface = "CV2X"

                with open(TESTING_DATA_LOG, 'a') as f:
                    f.write(f"Controller_Dealy from {current_interface} to {opposite_interface}: {Controller_Dealy * 1000} milliseconds\n")
                    f.write(f"Time_to_generate from {current_interface} to {opposite_interface}: {time_to_generate * 1000} milliseconds\n")
                    f.write(f"Time_to_send_FL from {current_interface} to {opposite_interface}: {time_to_send_fl * 1000} milliseconds\n")

                last_interface = current_interface

                T_r = None
                T_g = None
                T_s = None
                T_b = None
            return

        if 'NODE_ID' in data:
            node_id = data['NODE_ID']
            current_interface = data.get('Current interface', '*')
            speed = data.get('Speed', 40)  # Default speed if not provided
            if node_id not in received_nodes:
                received_nodes.append(node_id)

            if node_id not in df.index:
                send_initialization_flow_rule(node_id)
                new_row = pd.Series({col: None for col in df.columns}, name=node_id)
                new_row['NODE_ID'] = node_id
                new_row['Current interface'] = current_interface
                new_row['Speed'] = speed
                df = df._append(new_row)
                speed_data[node_id] = {'speed': speed, 'position': 0, 'direction': 1}
            else:
                if 'Current interface' in data:
                    previous_interface = df.at[node_id, 'Current interface']
                    df.at[node_id, 'Current interface'] = current_interface
                    df.at[node_id, 'Speed'] = speed
                    if current_interface != previous_interface:
                        current_interfaces[node_id] = current_interface
                        # Clear latency and power data when interface changes
                        clear_latency_and_power_data(node_id)
                        for i in range(1, 6):
                            threading.Timer(i, clear_latency_and_power_data, [node_id]).start()
                        threading.Timer(6, clear_node_parameters, [node_id]).start()
                        calculate_metrics = False
                        threading.Timer(10, restart_metrics_calculation).start()
                        if node_id in tx_rx_mapping.values():
                            send_execution_message_to_tx(node_id, current_interface)

            for key, value in data.items():
                df.at[node_id, key] = value

            # Check if both NODEs have sent their data
            if all(df.at[node, 'Current interface'] == current_interface and not df.loc[node, base_columns].isna().any()
                   for node in df.index):
                T_r = time.time()  # record T_r

            if 'Latency' in data:
                if node_id not in latency_data:
                    latency_data[node_id] = []
                latency_data[node_id].append(float(data['Latency'].replace('ms', '')))
                if len(latency_data[node_id]) > 5:
                    latency_data[node_id].pop(0)

            if 'Power' in data:
                power_value = float(data['Power'].split(',')[1])
                if power_value < 1000:
                    if node_id not in power_data:
                        power_data[node_id] = []
                    power_data[node_id].append(power_value)
                    if len(power_data[node_id]) > 5:
                        power_data[node_id].pop(0)

            display_df = df.dropna(axis=1, how='all')
            os.system('clear')
            for node_id in display_df.index:
                print(f"NODE_ID: {node_id}")
                node_df = display_df.loc[[node_id]].dropna(axis=1, how='all')
                print(node_df.to_string(index=False))
                print('\n')

        else:
            logging.error("Received data without NODE_ID")
    except Exception as e:
        logging.error(f"Error processing message: {e}")

def send_initialization_flow_rule(node_id):
    num = get_next_num()
    flow_rule = {
        'Num': num,
        'match': {
            'NODE_ID': node_id,
            'Src MAC': '*',
            'Des MAC': '*',
            'Src IP': '*',
            'Des IP': '*',
            'Src Port': '*',
            'Des Port': '*',
            'Current interface': '*'
        },
        'Command type': 'Initialization',
        'Value': 'Initialization',
        'Rx Power Threshold': 0,
        'Latency': '*',
        'Priority': 0,
        'Counter': 0,
        'Timeout': 20
    }
    logging.info(f"Sending initialization flow rule: {flow_rule}")
    client.publish(f"{MQTT_TOPIC_COMMAND}/{node_id}", json.dumps(flow_rule), qos=1)
    store_flow_rule(node_id, num, flow_rule)

def store_flow_rule(node_id, num, flow_rule):
    if node_id not in flow_rules:
        flow_rules[node_id] = {}
    flow_rules[node_id][num] = flow_rule
    with open(FLOWRULE_LOG, 'a') as f:
        f.write(json.dumps(flow_rule) + '\n')


def clear_latency_and_power_data(node_id):
    global latency_data, power_data
    latency_data[node_id] = []
    power_data[node_id] = []
    logging.info(f"Cleared latency and power data for NODE_ID: {node_id}")


def clear_node_parameters(node_id):
    global df
    df.loc[node_id, optional_columns] = None
    logging.info(f"Cleared parameters for NODE_ID: {node_id} after 5 seconds")


def restart_metrics_calculation():
    global calculate_metrics
    calculate_metrics = True
    logging.info("Restarted metrics calculation after 10 seconds")


def send_execution_message_to_tx(rx_node_id, rx_current_interface):
    global tx_rx_mapping, FLOWRULE_LOG
    tx_node_id = [k for k, v in tx_rx_mapping.items() if v == rx_node_id]
    if tx_node_id:
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


def check_and_judge(node_id):
    global df, latest_flow_rules, flow_rules, switching_nodes, latency_data, power_data, received_nodes

    avg_latency = None
    avg_power = None
    std_latency = None
    std_power = None

    if node_id in latency_data and len(latency_data[node_id]) == 5:
        avg_latency = np.mean(latency_data[node_id])
        std_latency = np.std(latency_data[node_id])
        logging.info(f"Average latency for NODE {node_id}: {avg_latency} ms, Std: {std_latency} ms")

        with open(CALCULATION_LATENCY_LOG, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - NODE_ID: {node_id} - Average Latency: {avg_latency} ms, Std: {std_latency} ms\n")

    if node_id in power_data and len(power_data[node_id]) == 5:
        avg_power = np.mean(power_data[node_id])
        std_power = np.std(power_data[node_id])
        logging.info(f"Average power for NODE {node_id}: {avg_power} dBm, Std: {std_power} dBm")

        with open(CALCULATION_POWER_LOG, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - NODE_ID: {node_id} - Average Power: {avg_power} dBm, Std: {std_power} dBm\n")

    if (avg_latency is not None and 20.0 <= avg_latency <= 60000) or \
       (avg_power is not None and -100 <= avg_power <= -75):
        handle_switching(node_id, 'latency' if avg_latency else 'power', avg_latency, std_latency, avg_power, std_power, '1,0' if avg_latency else '0,1')

    if (avg_latency is not None and (avg_latency > 60000 or avg_latency <= 0 or np.isnan(avg_latency))) or \
       (avg_power is not None and (avg_power < -100 or avg_power == 0 or np.isnan(avg_power))):

        if len(received_nodes) < 3:
            logging.warning("Not enough nodes for forwarding, skipping.")
            return
        
        third_node = received_nodes[2]
        if third_node in switching_nodes:
            logging.info(f"Skipping switching for {third_node}, already in progress.")
            return

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

        if not flow_rule_exists(abnormal_rx_node, "Initialization"):
            send_initialization_flow_rule(abnormal_rx_node)

        if not flow_rule_exists(third_node, switch_value):
            logging.info(f"Sending switching flow rule to third node {third_node} with Value: {switch_value}")
            
            if "ITSG5" in switch_value:
                send_itsg5_flow_rule(third_node, switch_value, '*', '*', '*', 'Tech switching')
            elif "CV2X" in switch_value:
                send_cv2x_flow_rule(third_node, switch_value, '*', '*', '*', 'Tech switching')

            switching_nodes.add(third_node)

            threading.Thread(target=wait_for_interface_update, args=(third_node, abnormal_rx_node)).start()


def wait_for_interface_update(third_node, rx_node):

    global df, latency_data, power_data, switching_nodes, latest_flow_rules

    target_interface = df.at[rx_node, 'Current interface'] if rx_node in df.index else '*'
    
    while True:
        time.sleep(1)

        if df.at[third_node, 'Current interface'] == target_interface:
            logging.info(f"Node {third_node} switched to {target_interface}, sending CLIENT.")

            send_forwarding_rule(third_node, rx_node, target_interface, "C")

            latency_data.clear()
            power_data.clear()
            logging.info("Cleared latency_data and power_data after sending CLIENT.")

            if third_node in switching_nodes:
                switching_nodes.remove(third_node)
                logging.info(f"Removed {third_node} from switching_nodes, allowing future switching.")
            received_nodes[2] = rx_node
            logging.info(f"Updated third_node to new rx_node: {rx_node}")

            latest_flow_rules = [rule for rule in latest_flow_rules if rule["NODE_ID"] != rx_node]
            logging.info(f"Cleared old abnormal rx_node records: {rx_node}")

            break

    while True:
        time.sleep(1)
        if third_node in df.index and pd.notna(df.at[third_node, "Src MAC"]):
            logging.info(f"Confirmed reception of {third_node}'s Src MAC. Proceeding with GROUP OWNER.")
            break

    send_forwarding_rule(rx_node, third_node, target_interface, "GO")


def flow_rule_exists(node_id, value):
    if node_id in flow_rules:
        for rule in flow_rules[node_id].values():
            if rule["Value"] == value:
                return True
    return False



def send_forwarding_rule(node_id, next_hop, forwarding_interface, value_type):
    global flow_rules, df
    next_hop_mac = df.at[next_hop, 'Src MAC'] if next_hop in df.index and pd.notna(df.at[next_hop, 'Src MAC']) else '*'

    existing_rules = flow_rules.get(node_id, {})
    for rule in existing_rules.values():
        if rule['Command type'] == 'Forwarding' and rule['Next hop'] == next_hop_mac:
            return

    num = get_next_num()
    flow_rule = {
        'Num': num,
        'match': {
            'NODE_ID': node_id,
            'Src MAC': '*',
            'Des MAC': '*',
            'Src IP': '*',
            'Des IP': '*',
            'Src Port': '*',
            'Des Port': '*',
            'Current interface': forwarding_interface
        },
        'Command type': 'Forwarding',
        'Value': value_type,
        'Next hop': next_hop_mac,
        'Rx Power Threshold': '*',
        'Latency': '*',
        'Priority': '*',
        'Counter': 0,
        'Timeout': 20
    }

    if node_id not in flow_rules:
        flow_rules[node_id] = {}
    flow_rules[node_id][num] = flow_rule

    logging.info(f"Sending Forwarding Rule: {flow_rule}")
    client.publish(f"{MQTT_TOPIC_COMMAND}/{node_id}", json.dumps(flow_rule), qos=1)
    store_flow_rule(node_id, num, flow_rule)


def handle_switching(node_id, trigger_type, avg_latency, std_latency, avg_power, std_power, priority):
    global flow_rules, current_interfaces, T_g
    T_g = time.time()  # record T_g
    current_interface = current_interfaces.get(node_id)

    if trigger_type == 'latency':
        if avg_latency + 2 * std_latency < 30:
            latency_value = avg_latency + 2 * std_latency
        else:
            latency_value = 30.0
        power_value = np.interp(avg_power, [-45, -10], [-70, -45])
    elif trigger_type == 'power':
        if avg_power - 2 * std_power > -80:
            power_value = avg_power - 2 * std_power
        else:
            power_value = -80.0
        latency_value = np.interp(avg_latency, [5, 20], [20, 25])

    if not flow_rules.get(node_id):
        send_flow_rule(node_id, latency_value, power_value, priority, current_interface)
    else:
        current_flow_rules = flow_rules[node_id]
        itsg5_rules_exist = any(rule['Value'].startswith('ITSG5') for rule in current_flow_rules.values())
        cv2x_rules_exist = any(rule['Value'].startswith('CV2X') for rule in current_flow_rules.values())

        if itsg5_rules_exist and cv2x_rules_exist:
            return

        if cv2x_rules_exist and current_interface == 'CV2X':
            send_flow_rule(node_id, latency_value, power_value, priority, 'CV2X')
        elif itsg5_rules_exist and current_interface == 'ITSG5':
            send_flow_rule(node_id, latency_value, power_value, priority, 'ITSG5')


def send_flow_rule(node_id, latency_value, power_value, priority, current_interface):
    global T_s, T_r, T_g
    T_s = time.time()  # record T_s
    if current_interface == 'ITSG5':
        send_cv2x_flow_rules(node_id, latency_value, power_value, priority, 'Tech switching')
    elif current_interface == 'CV2X':
        send_itsg5_flow_rules(node_id, latency_value, power_value, priority, 'Tech switching')
    else:
        send_cv2x_flow_rules(node_id, latency_value, power_value, priority, 'Tech switching')
        send_itsg5_flow_rules(node_id, latency_value, power_value, priority, 'Tech switching')


import threading

def send_initialization_flow_rule(node_id):
    global df

    num = get_next_num()
    flow_rule = {
        'Num': num,
        'match': {
            'NODE_ID': node_id,
            'Src MAC': '*',
            'Des MAC': '*',
            'Src IP': '*',
            'Des IP': '*',
            'Src Port': '*',
            'Des Port': '*',
            'Current interface': '*'
        },
        'Command type': 'Initialization',
        'Value': 'Initialization',
        'Rx Power Threshold': 0,
        'Latency': '*',
        'Priority': 0,
        'Counter': 0,
        'Timeout': 20
    }

    logging.info(f"Sending initialization flow rule: {flow_rule}")
    client.publish(f"{MQTT_TOPIC_COMMAND}/{node_id}", json.dumps(flow_rule), qos=1)
    store_flow_rule(node_id, num, flow_rule)

    if node_id in df.index:
        df.at[node_id, 'Current interface'] = '*' 
        df.at[node_id, 'Speed'] = 40
        def delayed_clear():
            for col in optional_columns:
                df.at[node_id, col] = None
            logging.info(f"Cleared optional_columns for NODE_ID: {node_id} after 2 seconds.")

        threading.Timer(5, delayed_clear).start()

    logging.info(f"Node {node_id} reset: Current interface = '*', Speed = 40, optional columns will be cleared after 2s.")




def send_itsg5_flow_rules(rx_node_id, latency_value, power_value, priority, command_type):
    global df, tx_rx_mapping
    node_ids = df.index.values
    for node in node_ids:
        if node == rx_node_id:
            send_itsg5_flow_rule(node, 'ITSG5_rx', latency_value, power_value, priority, command_type)
        else:
            send_itsg5_flow_rule(node, 'ITSG5_tx', '*', '*', '*', command_type)
            tx_rx_mapping[node] = rx_node_id


def send_cv2x_flow_rules(rx_node_id, latency_value, power_value, priority, command_type):
    global df, tx_rx_mapping
    node_ids = df.index.values
    for node in node_ids:
        if node == rx_node_id:
            send_cv2x_flow_rule(node, 'CV2X_rx', latency_value, power_value, priority, command_type)
        else:
            send_cv2x_flow_rule(node, 'CV2X_tx', '*', '*', '*', command_type)
            tx_rx_mapping[node] = rx_node_id


def calculate_timeout(node_id):
    global speed_data, COVERAGE
    speed = speed_data[node_id]['speed']
    position = speed_data[node_id]['position']
    direction = speed_data[node_id]['direction']

    # Calculate time to coverage boundary
    if direction == 1:
        time_to_boundary = (COVERAGE - position) / (speed * 1000 / 3600)  # Convert speed to m/s
    else:
        time_to_boundary = position / (speed * 1000 / 3600)  # Convert speed to m/s

    # Cap timeout between 10 and 150 seconds
    timeout = max(10, min(150, time_to_boundary))
    return timeout


def send_itsg5_flow_rule(node_id, action, latency_value, power_value, priority, command_type):
    global df
    num = get_next_num()
    match = {
        'NODE_ID': node_id,
        'Src MAC': df.at[node_id, 'Src MAC'] if df.at[node_id, 'Src MAC'] is not None else '*',
        'Des MAC': df.at[node_id, 'Des MAC'] if df.at[node_id, 'Des MAC'] is not None else '*',
        'Src IP': df.at[node_id, 'Src IP'] if df.at[node_id, 'Src IP'] is not None else '*',
        'Des IP': df.at[node_id, 'Des IP'] if df.at[node_id, 'Des IP'] is not None else '*',
        'Src Port': df.at[node_id, 'Src Port'] if df.at[node_id, 'Src Port'] is not None else '*',
        'Des Port': df.at[node_id, 'Des Port'] if df.at[node_id, 'Des Port'] is not None else '*',
        'Current interface': df.at[node_id, 'Current interface'] if df.at[
                                                                       node_id, 'Current interface'] is not None else '*'
    }
    timeout = calculate_timeout(node_id) if any(match[key] != '*' for key in match if key != 'NODE_ID') else 20
    flow_rule = {
        'Num': num,
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
    client.publish(f"{MQTT_TOPIC_COMMAND}/{node_id}", json.dumps(flow_rule), qos=1)
    store_flow_rule(node_id, num, flow_rule)


def send_cv2x_flow_rule(node_id, action, latency_value, power_value, priority, command_type):
    global df
    num = get_next_num()
    match = {
        'NODE_ID': node_id,
        'Src MAC': df.at[node_id, 'Src MAC'] if df.at[node_id, 'Src MAC'] is not None else '*',
        'Des MAC': df.at[node_id, 'Des MAC'] if df.at[node_id, 'Des MAC'] is not None else '*',
        'Src IP': df.at[node_id, 'Src IP'] if df.at[node_id, 'Src IP'] is not None else '*',
        'Des IP': df.at[node_id, 'Des IP'] if df.at[node_id, 'Des IP'] is not None else '*',
        'Src Port': df.at[node_id, 'Src Port'] if df.at[node_id, 'Src Port'] is not None else '*',
        'Des Port': df.at[node_id, 'Des Port'] if df.at[node_id, 'Des Port'] is not None else '*',
        'Current interface': df.at[node_id, 'Current interface'] if df.at[
                                                                       node_id, 'Current interface'] is not None else '*'
    }
    timeout = calculate_timeout(node_id) if any(match[key] != '*' for key in match if key != 'NODE_ID') else 20
    flow_rule = {
        'Num': num,
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
    client.publish(f"{MQTT_TOPIC_COMMAND}/{node_id}", json.dumps(flow_rule), qos=1)
    store_flow_rule(node_id, num, flow_rule)


def store_flow_rule(node_id, num, flow_rule):
    global flow_rules, latest_flow_rules
    if node_id not in flow_rules:
        flow_rules[node_id] = {}
    flow_rules[node_id][num] = flow_rule

    latest_flow_rules.append({'NODE_ID': node_id, 'Value': flow_rule['Value']})
    if len(latest_flow_rules) > 3:
        latest_flow_rules.pop(0)

    with open(FLOWRULE_LOG, 'a') as f:
        f.write(json.dumps(flow_rule) + '\n')



def handle_disabled_flow_rule(disabled_flow_rule):
    global flow_rules
    node_id = disabled_flow_rule['NODE_ID']
    num = disabled_flow_rule['Num']

    if node_id in flow_rules:
        if num in flow_rules[node_id]:
            del flow_rules[node_id][num]

        if not flow_rules[node_id]:
            del flow_rules[node_id]

    with open(DISABLE_FLOWRULE_LOG, 'a') as f:
        f.write(json.dumps(disabled_flow_rule) + '\n')
    check_and_judge(node_id)



def log_realtime_rules():
    global flow_rules
    while True:
        with open(REALTIME_RULE_LOG, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {json.dumps(flow_rules)}\n")
        time.sleep(10)


def monitor_metrics():
    global last_latency_data, last_power_data, calculate_metrics
    while True:
        time.sleep(5)
        if calculate_metrics:
            for node_id in latency_data:
                if len(latency_data[node_id]) == 5 and latency_data[node_id] != last_latency_data.get(node_id):
                    last_latency_data[node_id] = list(latency_data[node_id])
                    check_and_judge(node_id)
            for node_id in power_data:
                if len(power_data[node_id]) == 5 and power_data[node_id] != last_power_data.get(node_id):
                    last_power_data[node_id] = list(power_data[node_id])
                    check_and_judge(node_id)


def simulate_node_movement():
    global speed_data, COVERAGE
    while True:
        for node_id in speed_data:
            speed = speed_data[node_id]['speed']
            position = speed_data[node_id]['position']
            direction = speed_data[node_id]['direction']

            # Update position
            new_position = position + direction * (speed * 1000 / 3600) * 1  # Update every second

            if new_position >= COVERAGE or new_position <= 0:
                # Change direction if boundary is reached
                speed_data[node_id]['direction'] *= -1
                new_position = max(0, min(COVERAGE, new_position))

            speed_data[node_id]['position'] = new_position

        time.sleep(1)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Start the thread to log realtime rules, monitor metrics, and simulate NODE movement
threading.Thread(target=log_realtime_rules, daemon=True).start()
threading.Thread(target=monitor_metrics, daemon=True).start()
threading.Thread(target=simulate_node_movement, daemon=True).start()

client.loop_start()

os.system('clear')

while True:
    command = input("Enter command (itsg5n/cv2xn): ").strip().lower()

    if command == 'itsg5n' or command == 'cv2xn':
        if len(df.index) < 2:
            print("Error: Not enough nodes have sent data yet.")
            continue

        node_ids = list(df.index)[:2]
        if command == 'itsg5n':
            send_itsg5_flow_rule(node_ids[0], 'ITSG5_tx', '*', '*', '*', 'Tech switching')
            send_itsg5_flow_rule(node_ids[1], 'ITSG5_rx', '*', '*', '*', 'Tech switching')
            tx_rx_mapping[node_ids[0]] = node_ids[1]

        elif command == 'cv2xn':
            send_cv2x_flow_rule(node_ids[0], 'CV2X_tx', '*', '*', '*', 'Tech switching')
            send_cv2x_flow_rule(node_ids[1], 'CV2X_rx', '*', '*', '*', 'Tech switching')
            tx_rx_mapping[node_ids[0]] = node_ids[1]
    time.sleep(1)
