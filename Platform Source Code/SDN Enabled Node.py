#!/usr/bin/env python3

import logging
import paho.mqtt.client as mqtt
import json
import random
import string
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
import queue
import socket

# Configuration
MQTT_BROKER = '172.16.0.1'
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = 'node/command'
MQTT_TOPIC_DATA = 'node/data'
MQTT_TOPIC_DISABLE = 'node/disable'
MQTT_TOPIC_RECEIVED = 'node/received'
EXTRACTED_DATA_LOG = '/mnt/rw/log/extracted_data.log'
MATCH_INFO_LOG = '/mnt/rw/log/match_info.log'
REAL_TIME_RULES_LOG = '/mnt/rw/log/real_time_rules.log'
TXLOG_PATH = 'txlog.txt'
RXLOG_PATH = 'rxlog.txt'
LLC_RSSI_TX_LOG = '/mnt/rw/log/llc_rssi_tx.log'
LLC_RSSI_RX_LOG = '/mnt/rw/log/llc_rssi_rx.log'
LLC_TX_TEST_LOG = '/mnt/rw/log/llc_tx_test.log'
LLC_RX_TEST_LOG = '/mnt/rw/log/llc_rx_test.log'
LLC_CBR_LOG = '/mnt/rw/log/llc_cbr.log'
LOG_PATH_CV2X_TX = '/mnt/rw/log/cv2x_tx.log'
LOG_PATH_CV2X_RX = '/mnt/rw/log/cv2x_rx.log'
LOG_PATH_ACME_RX = '/mnt/rw/log/acme_lan/acme_rx.log'
CV2X_IFACES = {'tx': 'rmnet_usb1', 'rx': 'rmnet_usb1'}
EXECUTED_FLOW_VALUE_LOG = '/mnt/rw/log/executed_flow_value.log'

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Generate NODE ID
NODE_ID = ''.join(random.choices(string.digits, k=2)) + ''.join(random.choices(string.ascii_letters, k=2))
NODE_INFO = {'NODE_ID': NODE_ID, 'Speed': 40}  # Adding Speed parameter
current_capture_processes = []
current_tech = None
received_flow_rules = []
executed_flow_value = None  # New structure to store the last executed flow value
initialization_done = False
latency_threshold = float('inf')
power_threshold = float('inf')
latency_exceed_count = 0
power_exceed_count = 0
latency_zero_count = 0
power_zero_count = 0
waiting_for_executed = False
flow_rule_timeouts = {}
extract_timer = None
T_rf = None
T_e = {}
T_e_previous = {}

# Structure to store matching information
match_info = {}

# Track last processed line for PER and ACME
last_processed_line_per = None
last_processed_line_acme = None

# Forwading worker
FORWARDING_QUEUE = queue.Queue()
FORWARDING_SOCKET = None
FORWARDING_ACTIVE = False


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info(f"Connected to MQTT broker with result code {rc}")
        client.subscribe(f"{MQTT_TOPIC_COMMAND}/{NODE_ID}")
        send_own_info(client)
    else:
        logging.error(f"Failed to connect to MQTT broker with result code {rc}")


def send_own_info(client):
    global initialization_done
    if not initialization_done:
        logging.info(f"Sending NODE ID and Speed: {NODE_ID}, 40")
        client.publish(f"{MQTT_TOPIC_DATA}/{NODE_ID}", json.dumps(NODE_INFO), qos=1)

def on_message(client, userdata, msg):
    global waiting_for_executed, T_rf
    data = json.loads(msg.payload)
    logging.debug(f"Received message on topic {msg.topic}: {data}")

    if 'match' in data and data['match'].get('NODE_ID') == NODE_ID:
        process_flow_rule(data)
        display_flow_rules()
        if data['Value'] == 'Initialization':
            handle_initialization()
            increment_counter(data['Value'])
        else:
            evaluate_flow_rule(data)
            if 'rx' in data['Value'] and 'Latency' in data and data['Latency'] != '*':
                T_rf = time.time()
                logging.info(f"Setting T_rf to {T_rf} and sending Received message to controller")
                received_message = {"NODE_ID": NODE_ID, "Received": "True"}
                client.publish(MQTT_TOPIC_RECEIVED, json.dumps(received_message), qos=1)
                logging.info(f"Sent Received message to controller: {received_message}")
    elif 'Value' in data:
        run_value(data['Value'])


def handle_initialization():
    result = subprocess.run(['/mnt/rw/switch_tech.py', 'check'], capture_output=True, text=True)
    if "No technology is currently active" in result.stdout:
        pass
    else:
        subprocess.run(['/mnt/rw/switch_tech.py', 'disc'])
    global current_tech
    current_tech = None
    global initialization_done
    initialization_done = True


def process_flow_rule(data):
    global flow_rule_timeouts
    received_flow_rules.append(data)
    if 'Counter' not in data:
        data['Counter'] = 0
    timeout = data['Timeout']
    expiration_time = datetime.now() + timedelta(seconds=timeout)
    flow_rule_timeouts[data['Num']] = expiration_time


def display_flow_rules():
    os.system('clear')
    for rule in received_flow_rules:
        # Initialize a list to hold all key-value pairs in the desired format
        formatted_rule = []

        # Iterate over each key-value pair in the rule
        for key, value in rule.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    formatted_rule.append(f"{sub_key}: {sub_value}")
            else:
                formatted_rule.append(f"{key}: {value}")

        # Join the formatted key-value pairs using a vertical bar and print them
        print(" | ".join(formatted_rule))
        print('-' * 80)  # Print a separator line for better readability

def forwarding_worker():
    global FORWARDING_SOCKET, FORWARDING_ACTIVE
    while FORWARDING_ACTIVE:
        try:
            data = FORWARDING_QUEUE.get(timeout=1)
            if FORWARDING_SOCKET:
                FORWARDING_SOCKET.sendall((data + '\n').encode())
        except queue.Empty:
            continue
        except Exception as e:
            logging.error(f"[Forwarding] Send failed: {e}")
            FORWARDING_ACTIVE = False
            if FORWARDING_SOCKET:
                FORWARDING_SOCKET.close()
                FORWARDING_SOCKET = None


def evaluate_flow_rule(data):
    global latency_threshold, latency_exceed_count, waiting_for_executed
    latency_threshold = float('inf')
    latency_exceed_count = 0
    waiting_for_executed = False

    if 'Latency' in data and data['Latency'] != '*':
        try:
            latency_threshold = float(data['Latency'])
            logging.info(f"Set latency threshold to {latency_threshold} ms for evaluation")
        except ValueError:
            logging.warning(f"Invalid Latency value: {data['Latency']}")
    else:
        execute_flow_rule(data)  # No latency threshold, execute immediately


def execute_flow_rule(data):
    global current_tech, latency_threshold, power_threshold, latency_exceed_count, power_exceed_count, latency_zero_count, power_zero_count, waiting_for_executed, executed_flow_value
    stop_current_captures()
    value = data['Value']
    executed_flow_value = value  # Update the executed flow value
    latency_threshold = float('inf')
    power_threshold = float('inf')
    latency_exceed_count = 0
    power_exceed_count = 0
    latency_zero_count = 0
    power_zero_count = 0

    if 'Latency' in data and data['Latency'] != '*':
        try:
            latency_threshold = float(data['Latency'])
        except ValueError:
            logging.warning(f"Invalid Latency value: {data['Latency']}")

    if 'Rx Power Threshold' in data and data['Rx Power Threshold'] != '*':
        try:
            power_threshold = float(data['Rx Power Threshold'])
        except ValueError:
            logging.warning(f"Invalid Rx Power Threshold value: {data['Rx Power Threshold']}")

    match_criteria = ['Src MAC', 'Des MAC', 'Src IP', 'Des IP', 'Src Port', 'Des Port', 'Current interface']
    if all(data['match'].get(criteria) == '*' for criteria in match_criteria) and data['match'].get('NODE_ID') == NODE_ID:
        waiting_for_executed = False
        run_value(data['Value'])
    else:
        if latency_threshold != float('inf') or power_threshold != float('inf'):
            waiting_for_executed = True  # Ensure we check the values before execution

def run_value(value):
    global current_tech, waiting_for_executed, executed_flow_value, T_rf, T_e, T_e_previous, T_f
    global FORWARDING_SOCKET, FORWARDING_ACTIVE

    stop_current_captures()
    waiting_for_executed = True
    executed_flow_value = value
    log_executed_flow_value()

    # === Time recording (only for ITSG5/CV2X) ===
    if value not in ["C", "GO"]:
        if 'Latency' in received_flow_rules[-1] and received_flow_rules[-1]['Latency'] != '*':
            T_e_previous[value] = T_e.get(value, None)
            T_e[value] = time.time()
            if T_rf:
                time_to_switch = T_e[value] - T_rf
                logging.info(f"Time_to_switch for {value}: {time_to_switch * 1000:.2f} ms")
                with open('/mnt/rw/log/Data_Testing.log', 'a') as f:
                    f.write(f"Time_to_switch for {value}: {time_to_switch * 1000:.2f} ms\n")
                T_rf = None
            if T_e_previous[value]:
                time_to_next = T_e[value] - T_e_previous[value]
                logging.info(f"Time_to_next_executed for {value}: {time_to_next * 1000:.2f} ms")
                with open('/mnt/rw/log/Data_Testing.log', 'a') as f:
                    f.write(f"Time_to_next_executed for {value}: {time_to_next * 1000:.2f} ms\n")
                T_e_previous[value] = None

    # === Technology switching (ITSG5 / CV2X) ===
    if value.startswith('ITSG5'):
        NODE_INFO['current_tech'] = 'ITSG5'
        switch_tech_and_record_time(value, 'CV2X')
        current_tech = value
        threading.Timer(0, start_itsg5_ifconfig, [value]).start()
        for _ in range(3):
            send_current_interface(client, 'ITSG5')

    elif value.startswith('CV2X'):
        NODE_INFO['current_tech'] = 'CV2X'
        switch_tech_and_record_time(value, 'ITSG5')
        current_tech = value
        threading.Timer(0, start_cv2x_capture, [value.split('_')[-1]]).start()
        for _ in range(3):
            send_current_interface(client, 'CV2X')

    # === Forwarding: Wi-Fi Direct + Retry Logic ===
    if value in ["C", "GO"]:
        def run_forwarding():
            global FORWARDING_SOCKET, FORWARDING_ACTIVE
            next_hop_mac = None
            for rule in received_flow_rules:
                if rule["Value"] == value and rule["match"].get("NODE_ID") == NODE_ID:
                    next_hop_mac = rule.get("Next hop")
                    break

            if not next_hop_mac:
                logging.warning("No Next hop found for Forwarding rule.")
                return

            script_path = "/mnt/rw/wifi_p2p_client.py" if value == "C" else "/mnt/rw/wifi_p2p_server.py"
            try:
                if value == "C":
                    logging.info("[Forwarding] Waiting 20 seconds to ensure GO is ready...")
                    time.sleep(10)
                logging.info(f"[Forwarding] Executing {script_path} {next_hop_mac}")
                subprocess.Popen(["python3", script_path, next_hop_mac])
                time.sleep(3)
            except Exception as e:
                logging.error(f"[Forwarding] Script execution failed: {e}")
                return

            # === Retry socket connection ===
            max_retries = 5
            retry_delay = 3
            success = False

            for attempt in range(1, max_retries + 1):
                try:
                    logging.info(f"[Forwarding] Attempt {attempt}/{max_retries} to connect to GO socket...")
                    FORWARDING_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    FORWARDING_SOCKET.settimeout(10)
                    FORWARDING_SOCKET.connect(("192.168.49.1", 9000))
                    FORWARDING_ACTIVE = True
                    threading.Thread(target=forwarding_worker, daemon=True).start()
                    logging.info("[Forwarding] Socket connected and forwarding started.")
                    success = True
                    break
                except Exception as e:
                    logging.warning(f"[Forwarding] Attempt {attempt} failed: {e}")
                    time.sleep(retry_delay)

            if not success:
                logging.error("[Forwarding] All connection attempts failed.")
                FORWARDING_ACTIVE = False
                if FORWARDING_SOCKET:
                    FORWARDING_SOCKET.close()

        threading.Thread(target=run_forwarding, daemon=True).start()

    waiting_for_executed = False
    increment_counter(value)



def switch_tech_and_record_time(value, current_tech_prefix):
    global T_f
    process = subprocess.Popen(['/mnt/rw/switch_tech.py', value], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in iter(process.stdout.readline, b''):
        if b"successfully" in line:
            T_f = time.time()
            if T_e.get(value):
                duration_to_switch = T_f - T_e[value]
                current_tech_clean = current_tech_prefix.split('_')[0]
                value_clean = value.split('_')[0]
                logging.info(f"Duration_to_switch from {current_tech_clean} to {value_clean}: {duration_to_switch * 1000} milliseconds")
                with open('/mnt/rw/log/Testing_Data', 'a') as f:
                    f.write(f"Switched from {current_tech_clean} to {value_clean} in {duration_to_switch * 1000} milliseconds\n")
            break
    process.stdout.close()
    process.wait()


def send_current_interface(client, interface):
    data = {'NODE_ID': NODE_ID, 'Current interface': interface}
    client.publish(f"{MQTT_TOPIC_DATA}/{NODE_ID}", json.dumps(data), qos=1)


def increment_counter(value):
    for rule in received_flow_rules:
        if rule['Value'] == value:
            rule['Counter'] += 1
            break
    display_flow_rules()


def start_itsg5_ifconfig(action):
    if action == 'ITSG5_tx':
        subprocess.run(['ifconfig', 'cw-mon-tx', 'up'])
    elif action == 'ITSG5_rx':
        subprocess.run(['ifconfig', 'cw-mon-rx', 'up'])
    threading.Timer(0, start_itsg5_capture, [action]).start()


def start_itsg5_capture(action):
    if action == 'ITSG5_tx':
        subprocess.Popen(f"llc rcap --Interface cw-mon-tx --Meta --Dump > {LLC_RSSI_TX_LOG} 2>/dev/null", shell=True)
        subprocess.Popen(f"llc cbrmon 0x33 > {LLC_CBR_LOG} 2>/dev/null", shell=True)
    elif action == 'ITSG5_rx':
        subprocess.Popen(f"llc rcap --Interface cw-mon-rx --Meta --Dump > {LLC_RSSI_RX_LOG} 2>/dev/null", shell=True)
        subprocess.Popen(f"llc cbrmon 0x33 > {LLC_CBR_LOG} 2>/dev/null", shell=True)
    threading.Timer(0, start_periodic_extraction).start()


def start_cv2x_capture(direction):
    try:
        os.makedirs('/mnt/rw/log', exist_ok=True)
    except Exception as e:
        logging.error(f"Error creating log directory: {e}")
        return

    iface = CV2X_IFACES[direction]
    log_path = LOG_PATH_CV2X_TX if direction == 'tx' else LOG_PATH_CV2X_RX
    capture_command = f"sudo tcpdump -i {iface} -l -tttt > {log_path}"
    p = subprocess.Popen(capture_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    current_capture_processes.append(p)
    threading.Timer(0, start_periodic_extraction).start()


def calculate_sending_frequency(latency, timeout):
    min_frequency = 2  # Minimum 2 seconds
    max_frequency = 12  # Maximum 12 seconds
    latency_weight = (latency - 20) / (30 - 20)  # Latency weight (0 to 1)
    timeout_weight = (150 - timeout) / (150 - 10)  # Timeout weight (1 to 0)
    combined_weight = 0.5 * latency_weight + 0.5 * timeout_weight
    adjusted_frequency = min_frequency + (1 - combined_weight) * (max_frequency - min_frequency)
    return adjusted_frequency


def start_periodic_extraction():
    global extract_timer
    stop_periodic_extraction()

    # Get the latest received flow rule's latency and timeout
    if received_flow_rules:
        latest_rule = received_flow_rules[-1]  # Get the latest flow rule
        latency = latest_rule.get('Latency')
        timeout = latest_rule.get('Timeout')

        if latency is not None and timeout is not None:
            if latency == '*':
                frequency = 5
            else:
                latency = float(latency)
                frequency = calculate_sending_frequency(latency, timeout)
        else:
            frequency = 5
    else:
        frequency = 5  # Default frequency if no rules are received

    if current_tech == 'ITSG5_tx':
        extract_and_send_data(LLC_RSSI_TX_LOG, extract_rssi_data)
        extract_and_send_data(LLC_CBR_LOG, extract_cbr_data)
        extract_and_send_data(TXLOG_PATH, extract_tx_data)
        extract_and_send_data(LLC_TX_TEST_LOG, extract_tx_test_data)
    elif current_tech == 'ITSG5_rx':
        extract_and_send_data(LLC_RSSI_RX_LOG, extract_rssi_data)
        extract_and_send_data(LLC_CBR_LOG, extract_cbr_data)
        extract_and_send_data(RXLOG_PATH, extract_rx_data)
        extract_rx_test_data(LLC_RX_TEST_LOG)
    elif current_tech == 'CV2X_tx':
        extract_and_send_data(LOG_PATH_CV2X_TX, extract_cv2x_data)
    elif current_tech == 'CV2X_rx':
        extract_and_send_data(LOG_PATH_CV2X_RX, extract_cv2x_data)
        extract_and_send_acme_data(LOG_PATH_ACME_RX)

    extract_timer = threading.Timer(frequency, start_periodic_extraction)
    extract_timer.start()


def check_flow_rule_expiry():
    global received_flow_rules, flow_rule_timeouts
    current_time = datetime.now()
    for num, expiry in list(flow_rule_timeouts.items()):
        if current_time >= expiry:
            for rule in received_flow_rules:
                if rule['Num'] == num:
                    client.publish(MQTT_TOPIC_DISABLE, json.dumps({
                        'NODE_ID': rule['match']['NODE_ID'],
                        'Num': rule['Num'],
                        'Value': rule['Value']
                    }), qos=1)
                    received_flow_rules.remove(rule)
                    del flow_rule_timeouts[num]
                    break
    display_flow_rules()
    threading.Timer(5, check_flow_rule_expiry).start()

def extract_and_send_data(file_path, extract_func):
    global latency_zero_count, power_zero_count, waiting_for_executed
    global latency_exceed_count, power_exceed_count, executed_flow_value
    global FORWARDING_ACTIVE, FORWARDING_SOCKET

    latest_line = extract_second_latest_line(file_path)
    if latest_line:
        data = extract_func(latest_line)
        if data:
            data['NODE_ID'] = NODE_ID
            update_match_info(data)

            for rule in received_flow_rules:
                if 'Latency' in rule and 'Latency' in data:
                    try:
                        latency_value = float(data['Latency'].replace('ms', '').strip())
                        if latency_value > float(rule['Latency']):
                            latency_exceed_count += 1
                            latency_zero_count = 0
                        elif latency_value == 0:
                            latency_zero_count += 1
                        else:
                            latency_exceed_count = 0

                        if latency_exceed_count >= 3:
                            high_priority, low_priority = determine_priority()
                            if high_priority == 'Latency' and executed_flow_value != rule['Value']:
                                run_value(rule['Value'])
                                executed_flow_value = rule['Value']
                            latency_exceed_count = 0

                        if latency_zero_count > 10:
                            for rule in received_flow_rules:
                                if rule['Priority'] == '1,0' and executed_flow_value != rule['Value']:
                                    if 'Rx Power Threshold' in rule and 'Power' in data and rule['Rx Power Threshold'] != 'None':
                                        power_value = float(data['Power'].split(',')[1])
                                        if power_value < float(rule['Rx Power Threshold']):
                                            power_exceed_count += 1
                                            if power_exceed_count >= 3 or power_zero_count > 10:
                                                run_value(rule['Value'])
                                                executed_flow_value = rule['Value']
                                                power_exceed_count = 0
                            latency_zero_count = 0

                    except ValueError:
                        logging.warning(f"Invalid Latency value: {data['Latency']}")

                if 'Rx Power Threshold' in rule and 'Power' in data and rule['Rx Power Threshold'] != 'None':
                    try:
                        power_value = float(data['Power'].split(',')[1])
                        if power_value < float(rule['Rx Power Threshold']):
                            power_exceed_count += 1
                            power_zero_count = 0
                        elif power_value == 0:
                            power_zero_count += 1
                        else:
                            power_exceed_count = 0

                        if power_exceed_count >= 3:
                            high_priority, low_priority = determine_priority()
                            if high_priority == 'Power' and executed_flow_value != rule['Value']:
                                run_value(rule['Value'])
                                executed_flow_value = rule['Value']
                            power_exceed_count = 0

                        if power_zero_count > 10:
                            for rule in received_flow_rules:
                                if rule['Priority'] == '0,1' and executed_flow_value != rule['Value']:
                                    if 'Latency' in rule and 'Latency' in data:
                                        latency_value = float(data['Latency'].replace('ms', '').strip())
                                        if latency_value > float(rule['Latency']):
                                            latency_exceed_count += 1
                                            if latency_exceed_count >= 3 or latency_zero_count > 10:
                                                run_value(rule['Value'])
                                                executed_flow_value = rule['Value']
                                                latency_exceed_count = 0
                            power_zero_count = 0

                    except ValueError:
                        logging.warning(f"Invalid Power value: {data['Power']}")

            # ========== Real Time Socket Forwarding ==========
            if FORWARDING_ACTIVE and FORWARDING_SOCKET:
                try:
                    FORWARDING_SOCKET.sendall((json.dumps(data) + '\n').encode())
                    logging.debug("[Forwarding] Sent data via socket.")
                except Exception as e:
                    logging.error(f"[Forwarding] Failed to send via socket: {e}")
                    FORWARDING_ACTIVE = False
                    if FORWARDING_SOCKET:
                        FORWARDING_SOCKET.close()
                        FORWARDING_SOCKET = None

            # ========== MQTT Real Time Transmmit ==========
            if not waiting_for_executed:
                send_data_to_controller(data)

            # ========== Log Saving ==========
            with open(EXTRACTED_DATA_LOG, 'a') as f:
                f.write(json.dumps(data) + '\n')


def extract_second_latest_line(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r') as f:
        lines = f.readlines()
        if len(lines) < 2:
            return None
        for line in reversed(lines[:-1]):  # Skip the last line
            if not line.startswith('usec') and line.strip() and not line.startswith(
                    '#'):  # Ignore header and empty lines
                return line.strip()
    return None


def update_match_info(data):
    global match_info
    keys_to_check = ['NODE_ID', 'Src MAC', 'Des MAC', 'Src IP', 'Des IP', 'Src Port', 'Des Port']
    for key in keys_to_check:
        if key in data:
            match_info[key] = data[key]
    with open(MATCH_INFO_LOG, 'w') as f:
        f.write(json.dumps(match_info) + '\n')


def extract_rssi_data(line):
    parts = line.split(',')
    if len(parts) >= 11:
        return {
            'Payload': parts[3],
            'RSSI': f"{parts[4]},{parts[5]}",
            'DataRate': parts[6],
            'Position': f"{parts[9]},{parts[10]}".strip()
        }
    return None


def extract_cbr_data(line):
    parts = line.split()
    if len(parts) >= 8:
        freq = f"{parts[1]} {parts[2]} {parts[3].replace('(', '').replace(')', '')}MHz"
        cbr = parts[7].replace('(', '').replace(')', '')
        return {'Freq': freq, 'CBR': cbr}
    return None

def get_wifi_mac():
    interface = "wlan0"
    mac_address_path = f"/sys/class/net/{interface}/address"

    if os.path.exists(mac_address_path):
        with open(mac_address_path, "r") as f:
            mac_address = f.read().strip()
        return mac_address
    else:
        return None

def extract_tx_data(line):
    parts = line.split()
    if len(parts) >= 9:
        return {
            'Des MAC': parts[8],
            'Src MAC': get_wifi_mac()
        }
    return None


def extract_rx_data(line):
    parts = line.split()
    if len(parts) >= 19:
        latency_val = parts[10].lstrip('0')
        latency_ms = f"{int(latency_val) / 1000.0:.2f}ms"
        return {
            'Power': f"{parts[5]},{parts[6]}",
            'Noise': f"{parts[7]},{parts[8]}",
            'Timestamp': parts[9],
            'Latency': latency_ms,
            'Des MAC': parts[11],
            'Src MAC': get_wifi_mac()
        }
    return None


def extract_tx_test_data(line):
    parts = line.split()
    if len(parts) >= 9:
        pcr_value = parts[8].strip().replace(",", "") + "%"
        return {'PCR': pcr_value}
    return None


def extract_rx_test_data(file_path):
    global last_processed_line_per
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r') as f:
        lines = f.readlines()
        start_index = 0
        if last_processed_line_per in lines:
            start_index = lines.index(last_processed_line_per) + 1
        for line in lines[start_index:]:
            if 'Approx PER:' in line:
                parts = line.split()
                if len(parts) >= 6:
                    per_value = parts[3]
                    data = {'PER': per_value.strip()}
                    data['NODE_ID'] = NODE_ID
                    update_match_info(data)
                    with open(EXTRACTED_DATA_LOG, 'a') as f:
                        f.write(json.dumps(data) + '\n')
                    send_data_to_controller(data)
                last_processed_line_per = line
    return None


def extract_cv2x_data(line):
    parts = line.split()
    if len(parts) >= 9:
        timestamp = ' '.join(parts[0:2])
        src_ip, src_port = parts[3].rsplit('.', 1) if '.' in parts[3] else (parts[3], None)
        dst_ip, dst_port = parts[5].rsplit('.', 1) if '.' in parts[5] else (parts[5], None)
        if dst_port and dst_port.endswith(':'):
            dst_port = dst_port[:-1]
        payload = parts[-1].split(':')[-1]

        data = {
            'Timestamp': timestamp,
            'Src MAC': get_wifi_mac(),
            'Des MAC': None,
            'Src IP': src_ip,
            'Des IP': dst_ip,
            'Src Port': src_port,
            'Des Port': dst_port,
            'Payload': payload
        }
        return data
    return None


def extract_and_send_acme_data(file_path):
    global last_processed_line_acme, latency_exceed_count, latency_zero_count, waiting_for_executed, executed_flow_value
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r') as f:
        lines = f.readlines()
        start_index = 0
        if last_processed_line_acme in lines:
            start_index = lines.index(last_processed_line_acme) + 1
        for line in lines[start_index:]:
            if 'packets per second (PPS)' in line and 'avg latency' in line and 'CBP=' in line:
                parts = line.split('|')
                if len(parts) >= 7:
                    pps = parts[3].split()[0]
                    latency = ' '.join(parts[4].split()[0:2])
                    cbp = parts[6].split('=')[1].strip()
                    data = {
                        'PPS': pps,
                        'Latency': latency,
                        'CBP': cbp,
                        'NODE_ID': NODE_ID
                    }
                    update_match_info(data)

                    for rule in received_flow_rules:
                        if 'Latency' in rule and 'Latency' in data:
                            try:
                                latency_value = float(data['Latency'].replace('ms', '').strip())
                                if latency_value > float(rule['Latency']):
                                    latency_exceed_count += 1
                                    latency_zero_count = 0
                                elif latency_value == 0:
                                    latency_zero_count += 1
                                else:
                                    latency_exceed_count = 0
                                    latency_zero_count = 0  # Reset latency_zero_count if latency is not zero

                                if latency_exceed_count >= 3 or latency_zero_count > 10:
                                    high_priority, low_priority = determine_priority()
                                    if high_priority == 'Latency' and executed_flow_value != rule['Value']:
                                        run_value(rule['Value'])
                                        executed_flow_value = rule['Value']
                                    latency_exceed_count = 0
                                    latency_zero_count = 0  # Reset the count

                            except ValueError:
                                logging.warning(f"Invalid Latency value: {data['Latency']}")

                    with open(EXTRACTED_DATA_LOG, 'a') as f:
                        f.write(json.dumps(data) + '\n')
                    if not waiting_for_executed:
                        send_data_to_controller(data)

                last_processed_line_acme = line
    return None


def send_data_to_controller(data):
    global waiting_for_executed
    if not waiting_for_executed:
        client.publish(f"{MQTT_TOPIC_DATA}/{NODE_ID}", json.dumps(data), qos=1)


def stop_current_captures():
    global current_capture_processes
    for p in current_capture_processes:
        p.terminate()
    current_capture_processes = []


def stop_periodic_extraction():
    global extract_timer
    if extract_timer is not None:
        extract_timer.cancel()
        extract_timer = None


def determine_priority():
    high_priority = 'Latency'
    low_priority = 'Power'
    for rule in received_flow_rules:
        if rule['Priority'] == '0,1':
            high_priority = 'Power'
            low_priority = 'Latency'
            break
    return high_priority, low_priority


def log_received_flow_rules():
    with open(REAL_TIME_RULES_LOG, 'a') as f:
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'received_flow_rules': received_flow_rules
        }
        f.write(json.dumps(log_entry) + '\n')
    threading.Timer(10, log_received_flow_rules).start()


def log_executed_flow_value():
    global executed_flow_value
    if executed_flow_value is not None:
        with open(EXECUTED_FLOW_VALUE_LOG, 'a') as f:
            f.write(json.dumps(
                {'Value': executed_flow_value, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) + '\n')
    threading.Timer(10, log_executed_flow_value).start()


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

client.loop_start()

os.system('clear')

check_flow_rule_expiry()
log_received_flow_rules()
log_executed_flow_value()

while True:
    if not client.is_connected():
        client.reconnect()
    time.sleep(1)
