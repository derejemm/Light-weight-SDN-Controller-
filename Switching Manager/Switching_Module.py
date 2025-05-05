#!/usr/bin/env python3

import os
import sys
import subprocess
import random
import time
import warnings

# Ignore DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Define paths for various technologies
ACME_PATH = "/usr/bin/acme"
LOG_PATH = "/mnt/rw/log"
ACME_LOG_PATH = "/mnt/rw/log/acme_lan"

# Ensure that the log directory exists
if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

# Ensure that the acme log directory exists
if not os.path.exists(ACME_LOG_PATH):
    os.makedirs(ACME_LOG_PATH)


# Access to current technology
def get_current_tech():
    llc_processes = subprocess.run("pgrep -a -f 'llc -i'", shell=True, capture_output=True,
                                   text=True).stdout.strip().split('\n')
    llc_active = any(pid for pid in llc_processes if
                     pid and 'llc -i0 config' not in pid and 'llc -i1 count' not in pid and '[cw-llc' not in pid)

    etsa_processes = subprocess.run(["pgrep", "-x", "etsa"], capture_output=True, text=True).stdout.strip().split('\n')
    etsa_active = any(pid for pid in etsa_processes if pid)

    cv2x_active = subprocess.run(["systemctl", "is-active", "--quiet", "cv2x"]).returncode == 0

    acme_processes = subprocess.run(["pgrep", "-f", "acme"], capture_output=True, text=True).stdout.strip().split('\n')
    acme_active = any(pid for pid in acme_processes if pid)

    if cv2x_active or acme_active:
        return "CV2X"
    elif llc_active or etsa_active:
        return "ITSG5"
    else:
        return "NONE"


def confirm_current_tech():
    results = []
    for _ in range(5):  # Perform the check multiple times to ensure accuracy
        results.append(get_current_tech())
    return max(set(results), key=results.count)


# Placeholder for actual data reception check
def check_data_reception():
    # Implement actual logic to check if data is being received
    return random.choice([True, False])  # This is just a placeholder


# Check if ITSG5 communication is established
def check_ITS_G5_communication():
    print("Checking ITSG5 communication...")
    for _ in range(20):
        if check_data_reception():
            print("Successfully connected to ITSG5.")
            return True
        time.sleep(1)
    print("Failed to connect to ITSG5.")
    return False


# Check if CV2X communication is established (only for RX)
def check_CV2X_communication():
    print("Checking CV2X communication...")
    for _ in range(20):
        if check_data_reception():
            print("Successfully received data. Switched to CV2X.")
            return True
        time.sleep(1)
    print("Timeout. CV2X RX has closed.")
    return False


# Launch ITSG5_tx
def start_ITSG5_tx():
    print("Starting ITSG5 TX service...")
    subprocess.run(["sudo", "llc", "-i0", "chconfig", "-s", "-w", "CCH", "-c", "184", "-a", "3"],
                   stdout=open(f"{LOG_PATH}/llc_tx_chconfig.log", "w"), stderr=subprocess.STDOUT)
    tx_process = subprocess.Popen(
        ["sudo", "llc", "-i0", "test-tx", "-c", "184", "-a", "3", "-p", "30", "-m", "MK2MCS_R12QPSK", "-n", "100000",
         "-r", "100", "-l", "50", "-g", "time", "-f", "txlog.txt"], stdout=open(f"{LOG_PATH}/llc_tx_test.log", "w"),
        stderr=subprocess.STDOUT)
    if check_ITS_G5_communication():
        print("ITSG5 TX started successfully and is running in the background.")
    else:
        stop_current_tech()


# Launch ITSG5_rx
def start_ITSG5_rx():
    print("Starting ITSG5 RX service...")
    subprocess.run(["sudo", "llc", "-i0", "chconfig", "-s", "-w", "CCH", "-c", "184", "-a", "3"],
                   stdout=open(f"{LOG_PATH}/llc_tx_chconfig.log", "w"), stderr=subprocess.STDOUT)
    subprocess.run(["sudo", "llc", "-i1", "chconfig", "-s", "-w", "SCH", "-c", "184", "-a", "3"],
                   stdout=open(f"{LOG_PATH}/llc_rx_chconfig.log", "w"), stderr=subprocess.STDOUT)
    subprocess.Popen(["sudo", "llc", "-i1", "test-rx", "-c", "184", "-y", "-l", "-f", "rxlog.txt"],
                     stdout=open(f"{LOG_PATH}/llc_rx_test.log", "w"), stderr=subprocess.STDOUT)
    if check_ITS_G5_communication():
        print("ITSG5 RX started successfully and is running in the background.")
    else:
        stop_current_tech()


# Launch CV2X_tx
def start_CV2X_tx():
    print("Starting CV2X TX service...")
    subprocess.run(["sudo", "systemctl", "start", "cv2x"], stdout=open(f"{LOG_PATH}/cv2x_service.log", "w"),
                   stderr=subprocess.STDOUT)
    subprocess.Popen(["sudo", ACME_PATH, "-l", "300", "-W", "23,5,0", "-k", "10000"],
                     stdout=open(f"{ACME_LOG_PATH}/acme_tx.log", "w"), stderr=subprocess.STDOUT)
    print("CV2X TX is started successfully and is running in the background.")


# Launch CV2X_rx
def start_CV2X_rx():
    print("Starting CV2X RX service...")
    subprocess.run(["sudo", "systemctl", "start", "cv2x"], stdout=open(f"{LOG_PATH}/cv2x_service.log", "w"),
                   stderr=subprocess.STDOUT)
    subprocess.Popen(["sudo", ACME_PATH, "-R"], stdout=open(f"{ACME_LOG_PATH}/acme_rx.log", "w"),
                     stderr=subprocess.STDOUT)
    if check_CV2X_communication():
        print(
            "CV2X RX started successfully and is running in the background")
    else:
        stop_current_tech()


# Techniques for stopping current activities
def stop_current_tech():
    print("Attempting to stop current technology...")
    for i in range(5):
        print("Stopping etsa...")
        subprocess.run(["sudo", "pkill", "-9", "-f", "etsa"])
        print("Stopping llc...")

        # Get PIDs of llc processes, filtering out unwanted ones
        llc_processes = subprocess.run("pgrep -a -f 'llc -i'", shell=True, capture_output=True,
                                       text=True).stdout.strip().split('\n')
        for pid in llc_processes:
            if pid and 'llc -i0 config' not in pid and 'llc -i1 count' not in pid and '[cw-llc' not in pid:
                pid = pid.split()[0]  # Extract the PID
                print(f"Force killing llc process with PID: {pid}")
                subprocess.run(["sudo", "kill", "-9", pid])

        print("Stopping cv2x...")
        subprocess.run(["sudo", "systemctl", "stop", "cv2x"])
        print("Stopping acme...")
        subprocess.run(["sudo", "pkill", "-9", "-f", "acme"])

        # Verify that all processes are stopped
        llc_processes = subprocess.run("pgrep -a -f 'llc -i'", shell=True, capture_output=True,
                                       text=True).stdout.strip().split('\n')
        etsa_processes = subprocess.run(["pgrep", "-f", "etsa"], capture_output=True, text=True).stdout.strip().split(
            '\n')
        cv2x_active = subprocess.run(["systemctl", "is-active", "--quiet", "cv2x"]).returncode == 0
        acme_processes = subprocess.run(["pgrep", "-f", "acme"], capture_output=True, text=True).stdout.strip().split(
            '\n')

        llc_active = any(pid for pid in llc_processes if
                         pid and 'llc -i0 config' not in pid and 'llc -i1 count' not in pid and '[cw-llc' not in pid)
        etsa_active = any(pid for pid in etsa_processes if pid)
        acme_active = any(pid for pid in acme_processes if pid)

        print(f"llc active: {llc_active}")
        print(f"etsa active: {etsa_active}")
        print(f"cv2x active: {cv2x_active}")
        print(f"acme active: {acme_active}")

        if not llc_active and not etsa_active and not cv2x_active and not acme_active:
            print("All technologies stopped successfully.")
            return
        else:
            print("Failed to stop all technologies. Trying again...")
            time.sleep(2)

    print("Failed to stop technologies after 5 attempts.")
    exit(1)


# Disconnect current technology
def disconnect_current_tech():
    current_tech = confirm_current_tech()
    if current_tech != "NONE":
        print(f"Disconnecting current technology ({current_tech})...")
        stop_current_tech()
        print(f"Current technology is now NONE.")
    else:
        print("No technology is currently active.")


# Query current technology
def query_current_tech():
    current_tech = confirm_current_tech()
    if current_tech != "NONE":
        print(f"Current technology is {current_tech}.")
    else:
        print("No technology is currently active.")


# Function to display available operations
def display_available_operations():
    print("Available operations:")
    print("- check: Query current technology.")
    print("- disc: Disconnect current technology.")
    print("- ITSG5_tx: Start ITSG5 TX service.")
    print("- ITSG5_rx: Start ITSG5 RX service.")
    print("- CV2X_tx: Start CV2X TX service.")
    print("- CV2X_rx: Start CV2X RX service.")
    print("- help: Display available operations.")


# Main function
def main():
    if len(sys.argv) < 2:
        print("Usage: switch_tech.py [operation]")
        display_available_operations()
        exit(1)

    operation = sys.argv[1]

    if operation == "check":
        query_current_tech()
    elif operation == "disc":
        disconnect_current_tech()
    elif operation == "ITSG5_tx":
        current_tech = confirm_current_tech()
        if current_tech == "ITSG5":
            print("Already using ITSG5.")
        else:
            disconnect_current_tech()
            start_ITSG5_tx()
    elif operation == "ITSG5_rx":
        current_tech = confirm_current_tech()
        if current_tech == "ITSG5":
            print("Already using ITSG5.")
        else:
            disconnect_current_tech()
            start_ITSG5_rx()
    elif operation == "CV2X_tx":
        current_tech = confirm_current_tech()
        if current_tech == "CV2X":
            print("Already using CV2X.")
        else:
            disconnect_current_tech()
            start_CV2X_tx()
    elif operation == "CV2X_rx":
        current_tech = confirm_current_tech()
        if current_tech == "CV2X":
            print("Already using CV2X.")
        else:
            disconnect_current_tech()
            start_CV2X_rx()
    elif operation == "help":
        display_available_operations()
    else:
        print(f"Invalid operation: {operation}")
        display_available_operations()
        exit(1)


if __name__ == "__main__":
    main()
