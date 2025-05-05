#!/usr/bin/env python3
import subprocess
import time
import sys
import os
import socket

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def wait_for_go_ip(timeout=30):
    print("[Client] Waiting for GO to assign IP and become reachable...")
    for i in range(timeout):
        try:
            subprocess.check_output("ping -c 1 -W 1 192.168.49.1", shell=True)
            print(f"[Client] GO is reachable at attempt {i+1}.")
            return True
        except subprocess.CalledProcessError:
            print(f"[Client] GO not reachable yet... ({i+1}/{timeout})")
            time.sleep(1)
    print("[Client] GO is not reachable after timeout.")
    return False

def main(target_mac):
    print("[Client] Initializing Wi-Fi Direct...")
    run_cmd("killall wpa_supplicant")
    run_cmd("rm -rf /run/wpa_supplicant")
    run_cmd("mkdir -p /run/wpa_supplicant")
    run_cmd("chmod 770 /run/wpa_supplicant")
    run_cmd("wpa_supplicant -Dnl80211 -iwlan0 -c /etc/wpa_supplicant/p2p.conf -B -p /run/wpa_supplicant")

    print("[Client] Starting peer discovery...")
    run_cmd("wpa_cli -i wlan0 -p /run/wpa_supplicant p2p_find")

    peer_mac = ""
    for i in range(60):
        result = run_cmd("wpa_cli -i wlan0 -p /run/wpa_supplicant p2p_peers").stdout.strip().splitlines()
        if target_mac in result:
            peer_mac = target_mac
            print(f"[Client] Found GO: {peer_mac}")
            break
        print(f"[Client] Searching for GO... ({i+1})")
        time.sleep(2)

    if not peer_mac:
        print("[!] No GO found after timeout")
        sys.exit(1)

    run_cmd(f"wpa_cli -i wlan0 -p /run/wpa_supplicant p2p_connect {peer_mac} pbc")

    # Wait for p2p interface
    for _ in range(60):
        interfaces = os.listdir("/sys/class/net")
        p2p_if = next((i for i in interfaces if i.startswith("p2p-")), None)
        if p2p_if:
            print(f"[Client] Interface: {p2p_if}")
            break
        time.sleep(1)
    else:
        print("[!] Failed to get P2P interface")
        sys.exit(1)

    # Set IP manually (assuming GO is 192.168.49.1)
    run_cmd(f"ip link set {p2p_if} up")
    run_cmd(f"ifconfig {p2p_if} 192.168.49.2 netmask 255.255.255.0 up")

    # Wait until GO is pingable
    if not wait_for_go_ip():
        sys.exit(1)

    print("[Client] Wi-Fi Direct connection established and GO reachable.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: wifi_p2p_client.py <GO_MAC>")
        sys.exit(1)
    main(sys.argv[1])
