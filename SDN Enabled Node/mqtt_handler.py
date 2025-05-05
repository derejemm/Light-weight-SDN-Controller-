#!/usr/bin/env python3
# MQTT Communication Handler

import paho.mqtt.client as mqtt
import json
import logging
from config import *

# Initialize logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class MQTTHandler:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logging.info(f"Connected to MQTT broker")
            client.subscribe(f"{MQTT_TOPIC_COMMAND}/{NODE_ID}")
            self._send_own_info()
        else:
            logging.error(f"Connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            logging.debug(f"Received on {msg.topic}: {data}")
            return data  # Pass to main processing
        except Exception as e:
            logging.error(f"Message processing error: {e}")

    def _send_own_info(self):
        logging.info(f"Publishing node info: {NODE_INFO}")
        self.client.publish(f"{MQTT_TOPIC_DATA}/{NODE_ID}", json.dumps(NODE_INFO), qos=1)

    def connect(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

    def publish(self, topic, payload):
        self.client.publish(topic, json.dumps(payload), qos=1)

    def send_received_ack(self):
        ack = {"NODE_ID": NODE_ID, "Received": "True"}
        self.publish(MQTT_TOPIC_RECEIVED, ack)
        logging.info(f"Sent Received ACK: {ack}")

    def send_current_interface(self, interface):
        data = {'NODE_ID': NODE_ID, 'Current interface': interface}
        self.publish(f"{MQTT_TOPIC_DATA}/{NODE_ID}", data)
