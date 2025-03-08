import requests
import time
import socket
import ipaddress
import os
import logging

# Configuration (use environment variables or a config file for production)
SERVER_IP = os.environ.get("SERVER_IP", "192.168.1.100")  # Default IP
SERVER_URL = f"http://{SERVER_IP}:5000" # Changed to HTTP
LOG_FILE = "connectivity_log.txt"
CHECK_INTERVAL = 10  # seconds

# Configure logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def is_private_ip(ip):
    """Ensure the server IP is private before connecting."""
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        logging.error(f"Invalid IP address: {ip}")
        return False

if not is_private_ip(SERVER_IP):
    logging.error("Server IP is not private. Exiting.")
    exit(1)

def register_client():
    """Register the client with the server."""
    try:
        response = requests.post(f"{SERVER_URL}/register", timeout=5)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if data.get("status") == "success":
            logging.info("Registered successfully with server.")
            return True
        else:
            logging.error(f"Failed to register: {data.get('message')}")
            return False

    except requests.exceptions.RequestException as e:
        logging.error(f"Error registering with server: {e}")
        return False

def check_for_command():
    """Check if the server has sent a start/stop command."""
    try:
        response = requests.get(f"{SERVER_URL}/check_command", timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"Received command: {data}")  # Debugging
        if data.get("status") == "success":
            return data.get("command")
        else:
            logging.warning(f"Server returned: {data.get('message')}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error checking command: {e}")
        return None

def upload_log():
    """Upload the log file to the server."""
    if not os.path.exists(LOG_FILE):
        logging.info("No log file to upload.")
        return

    try:
        with open(LOG_FILE, "rb") as log:
            response = requests.post(f"{SERVER_URL}/upload_log", files={"log": log}, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                logging.info("Log uploaded successfully.")
                os.remove(LOG_FILE)  # Delete after successful upload
            else:
                logging.error(f"Log upload failed: {data.get('message')}")

    except (requests.exceptions.RequestException, OSError) as e:
        logging.error(f"Log upload failed: {e}")


def monitor_connection():
    """Monitor internet connectivity."""
    is_connected = True
    logging.info("Starting monitoring...")

    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            if not is_connected:
                logging.info("Reconnected")
                is_connected = True
        except OSError as e:
            if is_connected:
                logging.warning(f"Disconnected: {e}")
                is_connected = False

        # Check for stop command *before* sleeping to react promptly
        command = check_for_command()
        if command == "stop":
            logging.info("Stopping monitoring (command received).")
            break

        time.sleep(CHECK_INTERVAL)

    logging.info("Monitoring stopped.")
    upload_log()  # Upload the log *after* stopping


# Main execution flow
if __name__ == "__main__":
    if not register_client():
        exit(1)

    while True:
        command = check_for_command()

        if command == "start":
            monitor_connection()  # This function handles uploading the log
        elif command == "stop":
            logging.info("Monitoring is stopped (command received).")
        elif command is not None:
            logging.warning(f"Unknown command received: {command}")
        else:
            logging.info("No command received from server.")

        time.sleep(CHECK_INTERVAL)
