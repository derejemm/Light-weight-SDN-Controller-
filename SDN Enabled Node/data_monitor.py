#!/usr/bin/env python3
# Data Monitor - Maintains original extraction and analysis logic

import os
import json
import logging
from config import *

class DataMonitor:
    def __init__(self):
        self.last_processed_line_per = None
        self.last_processed_line_acme = None
        self.match_info = {}
        
    def extract_all_data(self, tech_type):
        """Original data extraction routing logic"""
        if tech_type == 'ITSG5_tx':
            self._extract_file(LLC_RSSI_TX_LOG, self._extract_rssi_data)
            self._extract_file(LLC_CBR_LOG, self._extract_cbr_data)
            self._extract_file(TXLOG_PATH, self._extract_tx_data)
            self._extract_file(LLC_TX_TEST_LOG, self._extract_tx_test_data)
        elif tech_type == 'ITSG5_rx':
            self._extract_file(LLC_RSSI_RX_LOG, self._extract_rssi_data)
            self._extract_file(LLC_CBR_LOG, self._extract_cbr_data)
            self._extract_file(RXLOG_PATH, self._extract_rx_data)
            self._extract_rx_test_data()
        elif tech_type == 'CV2X_tx':
            self._extract_file(CV2X_TX_LOG, self._extract_cv2x_data)
        elif tech_type == 'CV2X_rx':
            self._extract_file(CV2X_RX_LOG, self._extract_cv2x_data)
            self._extract_acme_data()

    def _extract_file(self, file_path, extract_func):
        """Original line processing logic"""
        line = self._get_second_latest_line(file_path)
        if line:
            data = extract_func(line)
            if data:
                self._process_extracted_data(data)

    def _get_second_latest_line(self, file_path):
        """Original line reading logic"""
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r') as f:
            lines = f.readlines()
            if len(lines) < 2:
                return None
                
            for line in reversed(lines[:-1]):
                if line.strip() and not line.startswith(('#', 'usec')):
                    return line.strip()
        return None

    def _process_extracted_data(self, data):
        """Original data processing pipeline"""
        data['NODE_ID'] = NODE_ID
        self._update_match_info(data)
        
        with open(EXTRACTED_DATA_LOG, 'a') as f:
            f.write(json.dumps(data) + '\n')

    def _update_match_info(self, data):
        """Original match info updating"""
        for key in ['NODE_ID', 'Src MAC', 'Des MAC', 
                   'Src IP', 'Des IP', 'Src Port', 'Des Port']:
            if key in data:
                self.match_info[key] = data[key]
                
        with open(MATCH_INFO_LOG, 'w') as f:
            f.write(json.dumps(self.match_info) + '\n')

    # Original extraction functions (kept verbatim)
    def _extract_rssi_data(self, line):
        parts = line.split(',')
        if len(parts) >= 11:
            return {
                'Payload': parts[3],
                'RSSI': f"{parts[4]},{parts[5]}",
                'DataRate': parts[6],
                'Position': f"{parts[9]},{parts[10]}".strip()
            }
        return None

    def _extract_cbr_data(self, line):
        parts = line.split()
        if len(parts) >= 8:
            return {
                'Freq': f"{parts[1]} {parts[2]} {parts[3].replace('(', '').replace(')', '')}MHz",
                'CBR': parts[7].replace('(', '').replace(')', '')
            }
        return None

    def _extract_tx_data(self, line):
        parts = line.split()
        if len(parts) >= 9:
            return {
                'Des MAC': parts[8],
                'Src MAC': self._get_wifi_mac()
            }
        return None

    def _extract_rx_data(self, line):
        parts = line.split()
        if len(parts) >= 19:
            latency_val = parts[10].lstrip('0')
            return {
                'Power': f"{parts[5]},{parts[6]}",
                'Noise': f"{parts[7]},{parts[8]}",
                'Timestamp': parts[9],
                'Latency': f"{int(latency_val) / 1000.0:.2f}ms",
                'Des MAC': parts[11],
                'Src MAC': self._get_wifi_mac()
            }
        return None

    def _extract_tx_test_data(self, line):
        parts = line.split()
        if len(parts) >= 9:
            return {'PCR': parts[8].strip().replace(",", "") + "%"}
        return None

    def _extract_rx_test_data(self):
        if not os.path.exists(LLC_RX_TEST_LOG):
            return
            
        with open(LLC_RX_TEST_LOG, 'r') as f:
            lines = f.readlines()
            
        start_idx = 0
        if self.last_processed_line_per in lines:
            start_idx = lines.index(self.last_processed_line_per) + 1
            
        for line in lines[start_idx:]:
            if 'Approx PER:' in line:
                parts = line.split()
                if len(parts) >= 6:
                    data = {'PER': parts[3].strip()}
                    self._process_extracted_data(data)
                self.last_processed_line_per = line

    def _extract_cv2x_data(self, line):
        parts = line.split()
        if len(parts) >= 9:
            src_ip, src_port = parts[3].rsplit('.', 1) if '.' in parts[3] else (parts[3], None)
            dst_ip, dst_port = parts[5].rsplit('.', 1) if '.' in parts[5] else (parts[5], None)
            dst_port = dst_port[:-1] if dst_port and dst_port.endswith(':') else dst_port
            
            return {
                'Timestamp': ' '.join(parts[0:2]),
                'Src MAC': self._get_wifi_mac(),
                'Src IP': src_ip,
                'Des IP': dst_ip,
                'Src Port': src_port,
                'Des Port': dst_port,
                'Payload': parts[-1].split(':')[-1]
            }
        return None

    def _extract_acme_data(self):
        if not os.path.exists(ACME_RX_LOG):
            return
            
        with open(ACME_RX_LOG, 'r') as f:
            lines = f.readlines()
            
        start_idx = 0
        if self.last_processed_line_acme in lines:
            start_idx = lines.index(self.last_processed_line_acme) + 1
            
        for line in lines[start_idx:]:
            if 'packets per second (PPS)' in line and 'avg latency' in line and 'CBP=' in line:
                parts = line.split('|')
                if len(parts) >= 7:
                    data = {
                        'PPS': parts[3].split()[0],
                        'Latency': ' '.join(parts[4].split()[0:2]),
                        'CBP': parts[6].split('=')[1].strip()
                    }
                    self._process_extracted_data(data)
                self.last_processed_line_acme = line

    def _get_wifi_mac(self):
        """Original MAC address fetching"""
        iface = "wlan0"
        path = f"/sys/class/net/{iface}/address"
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
        return None
