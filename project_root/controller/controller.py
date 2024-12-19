import logging
from mqtt_manager import MQTTManager
from flow_rule_manager import FlowRuleManager
from data_handler import DataHandler
from utils import get_current_timestamp

# Configuration parameters
MQTT_BROKER = "172.16.0.1"
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = "obu/command"
MQTT_TOPIC_DATA = "obu/data/#"
LOG_DIR = "logs"

# Initialize modules
mqtt_manager = MQTTManager(broker=MQTT_BROKER, port=MQTT_PORT, topics=[MQTT_TOPIC_DATA], on_message_callback=None)
flow_rule_manager = FlowRuleManager()
data_handler = DataHandler()


def handle_message(client, userdata, msg):
    """
    Handles incoming MQTT messages.
    """
    try:
        logging.info(f"Received message on topic {msg.topic}: {msg.payload}")
        data = mqtt_manager.parse_message(msg.payload)
        
        if "OBU_ID" in data:
            obu_id = data["OBU_ID"]
            logging.info(f"Processing message for OBU: {obu_id}")

            # Manage flow rules
            if "Latency" in data or "Power" in data:
                flow_rule_manager.add_rule(obu_id, data)

            # Handle latency and power data
            if "Latency" in data:
                latency = float(data["Latency"].replace("ms", ""))
                data_handler.add_latency(obu_id, latency)

            if "Power" in data:
                power = float(data["Power"].split(",")[1])
                data_handler.add_power(obu_id, power)

            # Check and trigger technology switch
            if data_handler.should_switch_technology(obu_id):
                new_tech = flow_rule_manager.get_next_technology(obu_id)
                if new_tech:
                    logging.info(f"Switching OBU {obu_id} to {new_tech}")
                    mqtt_manager.publish(MQTT_TOPIC_COMMAND, {"OBU_ID": obu_id, "Command": new_tech})

    except Exception as e:
        logging.error(f"Error handling message: {e}")


def start_controller():
    """
    Starts the SDN controller.
    """
    logging.info("Starting SDN Controller...")
    
    # Initialize MQTT client and start message loop
    mqtt_manager.set_message_callback(handle_message)
    mqtt_manager.connect()
    mqtt_manager.loop_start()

    try:
        while True:
            # Periodically log current status
            logging.info("Logging current status...")
            flow_rule_manager.log_rules()
            data_handler.log_data()
    except KeyboardInterrupt:
        logging.info("Stopping SDN Controller...")
        mqtt_manager.loop_stop()


if __name__ == "__main__":
    from logger import setup_logger

    # Configure logging
    setup_logger(log_dir=LOG_DIR, log_file="controller.log")

    # Start the SDN controller
    start_controller()
