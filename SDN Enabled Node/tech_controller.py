#!/usr/bin/env python3
# Technology Controller - Maintains original switching logic

import subprocess
import time
import threading
from config import *

class TechController:
    def __init__(self):
        self.current_capture_processes = []
        self.initialization_done = False
        self.extract_timer = None
        self.T_f = None

    def handle_initialization(self):
        """Original initialization sequence"""
        result = subprocess.run(
            ['/mnt/rw/switch_tech.py', 'check'],
            capture_output=True, 
            text=True
        )
        if "No technology is currently active" not in result.stdout:
            subprocess.run(['/mnt/rw/switch_tech.py', 'disc'])
        self.current_tech = None
        self.initialization_done = True

    def switch_technology(self, target_tech, current_tech_prefix):
        """Original tech switching with timing"""
        proc = subprocess.Popen(
            ['/mnt/rw/switch_tech.py', target_tech],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        for line in proc.stdout:
            if "successfully" in line:
                self.T_f = time.time()
                if hasattr(self, f"T_e_{target_tech}"):
                    duration = self.T_f - getattr(self, f"T_e_{target_tech}")
                    tech_from = current_tech_prefix.split('_')[0]
                    tech_to = target_tech.split('_')[0]
                    log_msg = (
                        f"Switched from {tech_from} to {tech_to} "
                        f"in {duration * 1000} milliseconds"
                    )
                    with open('/mnt/rw/log/Testing_Data', 'a') as f:
                        f.write(log_msg + '\n')
                break
        
        proc.stdout.close()
        proc.wait()

    def start_itsg5(self, action):
        """Original ITSG5 setup sequence"""
        if action == 'ITSG5_tx':
            subprocess.run(['ifconfig', 'cw-mon-tx', 'up'])
        elif action == 'ITSG5_rx':
            subprocess.run(['ifconfig', 'cw-mon-rx', 'up'])
        
        self._start_itsg5_capture(action)

    def _start_itsg5_capture(self, action):
        """Original capture process spawning"""
        if action == 'ITSG5_tx':
            cmd1 = f"llc rcap --Interface cw-mon-tx --Meta --Dump > {LLC_RSSI_TX_LOG} 2>/dev/null"
            cmd2 = f"llc cbrmon 0x33 > {LLC_CBR_LOG} 2>/dev/null"
        else:  # ITSG5_rx
            cmd1 = f"llc rcap --Interface cw-mon-rx --Meta --Dump > {LLC_RSSI_RX_LOG} 2>/dev/null"
            cmd2 = f"llc cbrmon 0x33 > {LLC_CBR_LOG} 2>/dev/null"
        
        self.current_capture_processes.append(subprocess.Popen(cmd1, shell=True))
        self.current_capture_processes.append(subprocess.Popen(cmd2, shell=True))
        self._schedule_extraction()

    def start_cv2x(self, direction):
        """Original CV2X capture setup"""
        try:
            os.makedirs('/mnt/rw/log', exist_ok=True)
        except Exception as e:
            logging.error(f"Directory creation failed: {e}")
            return

        iface = CV2X_IFACES[direction]
        log_path = CV2X_TX_LOG if direction == 'tx' else CV2X_RX_LOG
        cmd = f"sudo tcpdump -i {iface} -l -tttt > {log_path}"
        proc = subprocess.Popen(cmd, shell=True)
        self.current_capture_processes.append(proc)
        self._schedule_extraction()

    def stop_captures(self):
        """Original process termination"""
        for proc in self.current_capture_processes:
            proc.terminate()
        self.current_capture_processes = []

    def _schedule_extraction(self):
        """Original timer scheduling logic"""
        self._cancel_extraction_timer()
        self.extract_timer = threading.Timer(0, self._start_periodic_extraction)
        self.extract_timer.start()

    def _cancel_extraction_timer(self):
        """Original timer cancellation"""
        if self.extract_timer:
            self.extract_timer.cancel()
            self.extract_timer = None
