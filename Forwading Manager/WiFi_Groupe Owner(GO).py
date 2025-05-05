#!/usr/bin/env python3
import subprocess
import time
import sys
import os

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def main(target_mac):
    print("[GO] Initializing Wi-Fi Direct...")
    run_cmd("killall wpa_supplicant")
    run_cmd("rm -rf /run/wpa_supplicant")
    run_cmd("mkdir -p /run/wpa_supplicant")
    run_cmd("chmod 770 /run/wpa_supplicant")
    run_cmd("wpa_supplicant -Dnl80211 -iwlan0 -c /etc/wpa_supplicant/p2p.conf -B -p /run/wpa_supplicant")

    print("[GO] Starting peer discovery...")
    run_cmd("wpa_cli -i wlan0 -p /run/wpa_supplicant p2p_find")

    peer_mac = ""
    for i in range(60):
        result = run_cmd("wpa_cli -i wlan0 -p /run/wpa_supplicant p2p_peers").stdout.strip().splitlines()
        if target_mac in result:
            peer_mac = target_mac
            print(f"[GO] Found peer: {peer_mac}")
            break
        print(f"[GO] Waiting for peer... ({i+1})")
        time.sleep(2)

    if not peer_mac:
        print("[!] No peer found after timeout")
        sys.exit(1)

    run_cmd(f"wpa_cli -i wlan0 -p /run/wpa_supplicant p2p_connect {peer_mac} pbc")

    # Wait for P2P interface
    for _ in range(60):
        interfaces = os.listdir("/sys/class/net")
        p2p_if = next((i for i in interfaces if i.startswith("p2p-")), None)
        if p2p_if:
            print(f"[GO] Interface: {p2p_if}")
            break
        time.sleep(1)
    else:
        print("[!] Failed to get P2P interface")
        sys.exit(1)

    run_cmd(f"ip link set {p2p_if} up")
    run_cmd(f"ifconfig {p2p_if} 192.168.49.1 netmask 255.255.255.0 up")

    print("[GO] IP assigned, starting listener on port 9000...")
    with open("/mnt/rw/log/Forwarding_info.log", "w") as f:
        subprocess.run(["nc", "-l", "-p", "9000"], stdout=f)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: wifi_p2p_server.py <CLIENT_MAC>")
        sys.exit(1)
    main(sys.argv[1])
