import paho.mqtt.client as mqtt
import logging

class MQTTManager:
    def __init__(self, broker, port, topics, on_message_callback):
        self.client = mqtt.Client()
        self.broker = broker
        self.port = port
        self.topics = topics
        self.on_message_callback = on_message_callback
        self.client.on_connect = self.on_connect
        self.client.on_message = on_message_callback

    def connect(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            logging.info("Connected to MQTT broker")
        except Exception as e:
            logging.error(f"Failed to connect to MQTT broker: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Connected to MQTT broker successfully")
            for topic in self.topics:
                client.subscribe(topic)
                logging.info(f"Subscribed to topic: {topic}")
        else:
            logging.error(f"Connection to MQTT broker failed with code {rc}")

    def publish(self, topic, message):
        self.client.publish(topic, message)

    def loop_start(self):
        self.client.loop_start()
