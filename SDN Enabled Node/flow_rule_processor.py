#!/usr/bin/env python3
# Flow Rule Processing - Maintains original logic with minimal structure

import json
import time
import threading
from datetime import datetime, timedelta
import os
from config import *

class FlowRuleProcessor:
    def __init__(self):
        self.received_flow_rules = []
        self.flow_rule_timeouts = {}
        self.executed_flow_value = None
        self.current_tech = None
        self._init_state()

    def _init_state(self):
        self.latency_threshold = float('inf')
        self.power_threshold = float('inf') 
        self.latency_exceed_count = 0
        self.power_exceed_count = 0
        self.latency_zero_count = 0
        self.power_zero_count = 0
        self.waiting_for_executed = False
        self.T_rf = None
        self.T_e = {}
        self.T_e_previous = {}

    def process_rule(self, data):
        """Identical to original on_message processing"""
        if 'match' not in data or data['match'].get('NODE_ID') != NODE_ID:
            return False

        self.received_flow_rules.append(data)
        if 'Counter' not in data:
            data['Counter'] = 0
            
        timeout = data['Timeout']
        self.flow_rule_timeouts[data['Num']] = (
            datetime.now() + timedelta(seconds=timeout)
        )
        self.display_rules()
        
        if data['Value'] == 'Initialization':
            return 'INIT'
        else:
            self.evaluate_rule(data)
            if 'rx' in data['Value'] and data.get('Latency') != '*':
                self.T_rf = time.time()
                return 'ACK'
        return True

    def evaluate_rule(self, data):
        """Preserved threshold evaluation logic"""
        self.latency_threshold = float('inf')
        self.latency_exceed_count = 0
        self.waiting_for_executed = False

        if 'Latency' in data and data['Latency'] != '*':
            try:
                self.latency_threshold = float(data['Latency'])
            except ValueError:
                pass

    def check_timeouts(self):
        """Original timeout checking logic"""
        current_time = datetime.now()
        expired = []
        
        for num, expiry in self.flow_rule_timeouts.items():
            if current_time >= expiry:
                expired.append(num)
                
        for num in expired:
            for rule in self.received_flow_rules:
                if rule['Num'] == num:
                    yield {
                        'NODE_ID': rule['match']['NODE_ID'],
                        'Num': rule['Num'],
                        'Value': rule['Value']
                    }
                    self.received_flow_rules.remove(rule)
                    break
            del self.flow_rule_timeouts[num]
        
        self.display_rules()
        threading.Timer(5, self.check_timeouts).start()

    def display_rules(self):
        """Original display formatting"""
        os.system('clear')
        for rule in self.received_flow_rules:
            output = []
            for k, v in rule.items():
                if isinstance(v, dict):
                    output.extend(f"{sk}: {sv}" for sk, sv in v.items())
                else:
                    output.append(f"{k}: {v}")
            print(" | ".join(output))
            print('-' * 80)

    def increment_counter(self, value):
        """Original counter logic"""
        for rule in self.received_flow_rules:
            if rule['Value'] == value:
                rule['Counter'] += 1
                break
        self.display_rules()
