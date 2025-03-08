from flask import Flask, request, jsonify, render_template
from flask_restful import Api, Resource
import os
import sqlite3
from datetime import datetime
import ipaddress

app = Flask(__name__)
api = Api(app)

LOG_DIR = "client_logs"
DB_FILE = "clients.db"
os.makedirs(LOG_DIR, exist_ok=True)

# Ensure the database exists
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT UNIQUE NOT NULL,
                last_checkin TEXT,
                status TEXT DEFAULT 'inactive'
            )
        ''')
        conn.commit()

init_db()

def is_private_ip(ip):
    """Check if an IP address is private."""
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False

# --- Web UI Routes ---
@app.route('/')
def dashboard():
    """Main dashboard displaying all registered clients."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ip, last_checkin, status FROM clients")
        clients = cursor.fetchall()  # List of tuples (ip, last_checkin, status)

    return render_template('index.html', clients=clients)

@app.route('/logs')
def logs():
    """Page to view uploaded logs."""
    log_files = os.listdir(LOG_DIR) if os.path.exists(LOG_DIR) else []
    return render_template('logs.html', log_files=log_files)

@app.route('/analytics')
def analytics():
    """Page to view connection analytics."""
    return render_template('analytics.html')

# --- API Routes ---
class ClientRegister(Resource):
    def post(self):
        client_ip = request.remote_addr
        if not is_private_ip(client_ip):
            return jsonify({"status": "fail", "message": "Public IPs are not allowed."})

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO clients (ip, last_checkin, status) VALUES (?, ?, ?) ON CONFLICT(ip) DO UPDATE SET last_checkin=?, status='active'",
                               (client_ip, datetime.now().isoformat(), 'active', datetime.now().isoformat()))
                conn.commit()
                return jsonify({"status": "success", "message": "Client registered successfully."})
            except sqlite3.Error as e:
                return jsonify({"status": "fail", "message": f"Database error: {str(e)}"})

class ControlClients(Resource):
    def get(self):
        command = request.args.get('command')
        if command not in ['start', 'stop']:
            return jsonify({"status": "fail", "message": "Invalid command. Use 'start' or 'stop'."})

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE clients SET status = ?", (command,))
                conn.commit()
                return jsonify({"status": "success", "message": f"Command '{command}' sent to clients."})
            except sqlite3.Error as e:
                return jsonify({"status": "fail", "message": f"Database error: {str(e)}"})

class ClientCheck(Resource):
    def get(self):
        client_ip = request.remote_addr
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT status FROM clients WHERE ip = ?", (client_ip,))
                result = cursor.fetchone()
                if result:
                    return jsonify({"status": "success", "command": result[0]})
                return jsonify({"status": "fail", "message": "Client not registered."})
            except sqlite3.Error as e:
                return jsonify({"status": "fail", "message": f"Database error: {str(e)}"})

class LogUpload(Resource):
    def post(self):
        client_ip = request.remote_addr
        file = request.files.get('log')

        if not file:
            return jsonify({"status": "fail", "message": "No log file provided."})

        filename = os.path.join(LOG_DIR, f"{client_ip}_{datetime.now().strftime('%Y%m%d%H%M%S')}.log")
        try:
            file.save(filename)
            return jsonify({"status": "success", "message": "Log uploaded successfully."})
        except Exception as e:
            return jsonify({"status": "fail", "message": f"Error saving log: {str(e)}"})

# Register Resources
api.add_resource(ClientRegister, '/register')
api.add_resource(ControlClients, '/control_clients')
api.add_resource(ClientCheck, '/check_command')
api.add_resource(LogUpload, '/upload_log')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
