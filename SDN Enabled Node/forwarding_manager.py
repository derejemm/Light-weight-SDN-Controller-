#!/usr/bin/env python3
# Forwarding Manager - Original Wi-Fi Direct and socket handling

import socket
import queue
import threading
import time
import logging
from config import *

class ForwardingManager:
    def __init__(self):
        self.forwarding_queue = queue.Queue()
        self.forwarding_socket = None
        self.forwarding_active = False
        self.worker_thread = None

    def start_forwarding(self, role, next_hop_mac):
        """Original forwarding setup logic"""
        def forwarding_worker():
            while self.forwarding_active:
                try:
                    data = self.forwarding_queue.get(timeout=1)
                    if self.forwarding_socket:
                        self.forwarding_socket.sendall((data + '\n').encode())
                except queue.Empty:
                    continue
                except Exception as e:
                    logging.error(f"[Forwarding] Send failed: {e}")
                    self._cleanup_forwarding()
                    break

        def execute_forwarding():
            script = "/mnt/rw/wifi_p2p_server.py" if role == "GO" else "/mnt/rw/wifi_p2p_client.py"
            
            if role == "C":
                time.sleep(10)  # Original wait time
            
            try:
                subprocess.Popen(["python3", script, next_hop_mac])
                time.sleep(3)  # Original delay
            except Exception as e:
                logging.error(f"[Forwarding] Script failed: {e}")
                return

            # Original socket connection logic with retries
            max_retries = 5
            for attempt in range(1, max_retries + 1):
                try:
                    self.forwarding_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.forwarding_socket.settimeout(10)
                    self.forwarding_socket.connect(("192.168.49.1", 9000))
                    self.forwarding_active = True
                    self.worker_thread = threading.Thread(target=forwarding_worker, daemon=True)
                    self.worker_thread.start()
                    break
                except Exception as e:
                    if attempt == max_retries:
                        logging.error("[Forwarding] All attempts failed")
                        self._cleanup_forwarding()
                    time.sleep(3)  # Original retry delay

        threading.Thread(target=execute_forwarding, daemon=True).start()

    def _cleanup_forwarding(self):
        """Original cleanup procedure"""
        self.forwarding_active = False
        if self.forwarding_socket:
            self.forwarding_socket.close()
            self.forwarding_socket = None

    def enqueue_data(self, data):
        """Original queueing mechanism"""
        if self.forwarding_active:
            try:
                self.forwarding_queue.put(json.dumps(data))
            except Exception as e:
                logging.error(f"[Forwarding] Enqueue failed: {e}")

    def stop_forwarding(self):
        """Original stopping logic"""
        self._cleanup_forwarding()
        if self.worker_thread:
            self.worker_thread.join(timeout=1)
