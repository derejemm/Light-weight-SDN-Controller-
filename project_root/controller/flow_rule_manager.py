import json
import logging

class FlowRuleManager:
    def __init__(self):
        self.flow_rules = {}

    def add_rule(self, rule):
        rule_id = rule['Num']
        self.flow_rules[rule_id] = rule
        logging.info(f"Added flow rule: {json.dumps(rule)}")

    def remove_rule(self, rule_id):
        if rule_id in self.flow_rules:
            del self.flow_rules[rule_id]
            logging.info(f"Removed flow rule: {rule_id}")
