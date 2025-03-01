import requests
import time
import socket
import ipaddress
import os

SERVER_IP = "192.168.1.100"  # Replace with your server IP
SERVER_URL = f"http://{SERVER_IP}:5000"

LOG_FILE = "connectivity_log.txt"

def is_private_ip(ip):
    """Ensure the server IP is private before connecting."""
    return ipaddress.ip_address(ip).is_private

if not is_private_ip(SERVER_IP):
    print("Error: Server IP is not private. Exiting.")
    exit(1)

def register_client():
    """Register the client with the server."""
    try:
        response = requests.post(f"{SERVER_URL}/register", timeout=5)
        if response.json().get("status") == "success":
            print("Registered successfully with server.")
        else:
            print("Failed to register:", response.json().get("message"))
            exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error registering with server: {e}")
        exit(1)

def check_for_command():
    """Check if the server has sent a start/stop command."""
    try:
        response = requests.get(f"{SERVER_URL}/check_command", timeout=5)
        data = response.json()
        if data.get("status") == "success":
            return data.get("command")
    except requests.exceptions.RequestException as e:
        print(f"Error checking command: {e}")
    return None

def upload_log():
    """Upload the log file to the server."""
    if not os.path.exists(LOG_FILE):
        return
    
    with open(LOG_FILE, "rb") as log:
        try:
            response = requests.post(f"{SERVER_URL}/upload_log", files={"log": log}, timeout=5)
            if response.json().get("status") == "success":
                print("Log uploaded successfully.")
                os.remove(LOG_FILE)  # Delete after successful upload
        except requests.exceptions.RequestException as e:
            print(f"Log upload failed: {e}")

def monitor_connection():
    """Monitor internet connectivity."""
    is_connected = True
    with open(LOG_FILE, "w") as log:
        while True:
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=5)
                if not is_connected:
                    log.write("Reconnected at {}\n".format(time.ctime()))
                    is_connected = True
            except OSError:
                if is_connected:
                    log.write("Disconnected at {}\n".format(time.ctime()))
                    is_connected = False
            
            time.sleep(10)  # Check every 10 seconds
            
            # Check for stop command
            if check_for_command() == "stop":
                print("Stopping monitoring...")
                break

register_client()

while True:
    command = check_for_command()
    if command == "start":
        print("Starting monitoring...")
        monitor_connection()
        upload_log()
    elif command == "stop":
        print("Monitoring is stopped.")
    
    print("No command received. Checking again in 10 seconds...")
    time.sleep(10)
