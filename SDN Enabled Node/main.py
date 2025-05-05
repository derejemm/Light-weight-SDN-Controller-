#!/usr/bin/env python3
# Main Application - Preserves original execution structure

import os
import time
import threading
from config import *
from mqtt_handler import MQTTHandler
from flow_rule_processor import FlowRuleProcessor
from tech_controller import TechController
from data_monitor import DataMonitor
from forwarding_manager import ForwardingManager

class NodeApplication:
    def __init__(self):
        # Initialize all components
        self.mqtt = MQTTHandler()
        self.flow_rules = FlowRuleProcessor()
        self.tech = TechController()
        self.monitor = DataMonitor()
        self.forwarding = ForwardingManager()
        
        # Original global state tracking
        self.initialization_done = False
        self.current_tech = None
        self.executed_flow_value = None

    def start(self):
        """Original startup sequence"""
        os.system('clear')
        
        # Start MQTT connection
        self.mqtt.connect()
        
        # Start background threads
        threading.Thread(target=self._check_flow_rules).start()
        threading.Thread(target=self._log_received_rules).start()
        threading.Thread(target=self._log_executed_values).start()
        
        # Main loop
        while True:
            if not self.mqtt.connected:
                self.mqtt.connect()
            time.sleep(1)

    def _check_flow_rules(self):
        """Original rule checking thread"""
        while True:
            for expired_rule in self.flow_rules.check_timeouts():
                self.mqtt.publish(MQTT_TOPIC_DISABLE, expired_rule)
            time.sleep(5)

    def _log_received_rules(self):
        """Original rule logging thread"""
        while True:
            with open(REAL_TIME_RULES_LOG, 'a') as f:
                f.write(json.dumps({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'rules': self.flow_rules.received_flow_rules
                }) + '\n')
            time.sleep(10)

    def _log_executed_values(self):
        """Original value logging thread"""
        while True:
            if self.executed_flow_value:
                with open(EXECUTED_FLOW_VALUE_LOG, 'a') as f:
                    f.write(json.dumps({
                        'Value': self.executed_flow_value,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }) + '\n')
            time.sleep(10)

    def process_message(self, msg):
        """Original message processing pipeline"""
        data = json.loads(msg.payload)
        
        # Flow rule handling
        if 'match' in data:
            result = self.flow_rules.process_rule(data)
            if result == 'INIT':
                self.tech.handle_initialization()
                self.flow_rules.increment_counter('Initialization')
            elif result == 'ACK':
                self.mqtt.send_received_ack()
        
        # Value execution
        elif 'Value' in data:
            self._execute_value(data['Value'])

    def _execute_value(self, value):
        """Original value execution logic"""
        self.executed_flow_value = value
        self.tech.stop_captures()
        
        if value.startswith(('ITSG5', 'CV2X')):
            self._handle_tech_switch(value)
        elif value in ('C', 'GO'):
            self._handle_forwarding(value)

    def _handle_tech_switch(self, value):
        """Original technology switching"""
        tech_type = value.split('_')[-1]
        opposite_tech = 'ITSG5' if 'CV2X' in value else 'CV2X'
        
        if value.startswith('ITSG5'):
            self.tech.start_itsg5(value)
        else:
            self.tech.start_cv2x(tech_type)
            
        self.current_tech = value
        for _ in range(3):  # Original 3x interface announcement
            self.mqtt.send_current_interface(
                'ITSG5' if 'ITSG5' in value else 'CV2X'
            )

    def _handle_forwarding(self, role):
        """Original forwarding setup"""
        next_hop_mac = None
        for rule in self.flow_rules.received_flow_rules:
            if rule["Value"] == role and rule["match"].get("NODE_ID") == NODE_ID:
                next_hop_mac = rule.get("Next hop")
                break
                
        if next_hop_mac:
            self.forwarding.start_forwarding(role, next_hop_mac)

if __name__ == "__main__":
    app = NodeApplication()
    app.start()
