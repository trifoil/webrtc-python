#!/usr/bin/env python3

import asyncio
import time
import psutil
import subprocess

def find_webrtc_processes():
    """Find running WebRTC sender and receiver processes"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python' and proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'sender.py' in cmdline or 'receiver.py' in cmdline:
                    processes.append({
                        'pid': proc.info['pid'],
                        'type': 'sender' if 'sender.py' in cmdline else 'receiver',
                        'cmdline': cmdline
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return processes

def check_network_connectivity(host, port):
    """Check if network port is accessible"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

async def monitor_connection():
    """Monitor WebRTC connection health"""
    print("WebRTC Connection Monitor")
    print("=" * 40)
    
    while True:
        # Check processes
        processes = find_webrtc_processes()
        sender_running = any(p['type'] == 'sender' for p in processes)
        receiver_running = any(p['type'] == 'receiver' for p in processes)
        
        # Check network
        network_ok = check_network_connectivity("10.10.1.100", 9999)
        
        # Display status
        timestamp = time.strftime("%H:%M:%S")
        print(f"\n[{timestamp}] Connection Status:")
        print(f"  Sender:    {'✓ Running' if sender_running else '✗ Not running'}")
        print(f"  Receiver:  {'✓ Running' if receiver_running else '✗ Not running'}")
        print(f"  Network:   {'✓ Connected' if network_ok else '✗ Disconnected'}")
        
        if processes:
            print("\nActive processes:")
            for proc in processes:
                print(f"  {proc['type'].title()}: PID {proc['pid']}")
        
        # Recommendations
        if not sender_running:
            print("\n⚠️  Sender not running. Start with: python sender.py")
        if not receiver_running:
            print("\n⚠️  Receiver not running. Start with: python receiver.py")
        if not network_ok:
            print("\n⚠️  Network connectivity issue. Check IP address and firewall.")
        
        if sender_running and receiver_running and network_ok:
            print("\n✓ All systems operational!")
        
        await asyncio.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    try:
        asyncio.run(monitor_connection())
    except KeyboardInterrupt:
        print("\nMonitoring stopped.") 