from flask import Flask, jsonify, request, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import env  # env.py file
import datetime
import subprocess

app = Flask(__name__)

# Define your API key HERE
API_KEY = env.API_KEY

def get_real_ip():
    """Function to get the real IP address from Cloudflare headers (if applicable)"""
    if request.headers.get('CF-Connecting-IP'):
        return request.headers.get('CF-Connecting-IP')
    return request.remote_addr

limiter = Limiter(
    get_real_ip,
    app=app,
    #default_limits=["200 per day", "50 per hour"]
)

def get_current_time():
    """Function to get the current time"""
    time_str = datetime.datetime.now().strftime("%b %d %H:%M:%S")
    return time_str

def get_ipv4_addr():
    """Function to get the IPv4 address"""
    # Run `hostname -I` and capture output
    result = subprocess.run(["hostname", "-I"], stdout=subprocess.PIPE, text=True)
    ip_addr = result.stdout.strip()
    return ip_addr

def get_cpu_usage():
    """Function to get CPU usage"""
    # Run the `top` command
    result = subprocess.run(["top", "-bn1"], stdout=subprocess.PIPE, text=True)
    
    # Extract the line with CPU information
    for line in result.stdout.splitlines():
        if "Cpu(s)" in line:
            parts = line.split()
            user = float(parts[1].strip('%us,'))
            system = float(parts[3].strip('%sy,'))
            cpu_usage = user + system
            return f"{cpu_usage:.0f}%"

def get_soc_temp():
    """Function to get SoC temperature"""
    # Run `vcgencmd measure_temp` and capture output
    result = subprocess.run(["vcgencmd", "measure_temp"], stdout=subprocess.PIPE, text=True)
    cpu_temp = result.stdout.strip().replace("temp=", "").replace("'C", "C")
    return cpu_temp

def get_memory_stats():
    """Function to get memory statistics"""
    with open('/proc/meminfo', 'r') as meminfo:
        lines = meminfo.readlines()

    # Extract information from /proc/meminfo
    mem_info = {}
    for line in lines:
        parts = line.split()
        mem_info[parts[0].rstrip(':')] = float(parts[1])

    # Calculate RAM usage
    total_ram = mem_info['MemTotal'] / 1024  # Convert from kB to MB
    available_ram = mem_info['MemAvailable'] / 1024  # Convert from kB to MB
    used_ram = total_ram - available_ram

    # Calculate swap usage
    total_swap = mem_info['SwapTotal'] / 1024  # Convert from kB to MB
    free_swap = mem_info['SwapFree'] / 1024  # Convert from kB to MB
    used_swap = total_swap - free_swap

    return total_ram, used_ram, total_swap, used_swap

@app.route("/")
@limiter.limit("1 per 2 seconds")
def root():
    """Render the main HTML page"""
    return render_template('index.html')

@app.route("/api/time", methods=['GET'])
@limiter.limit("15 per minute")
def api_time():
    """Return the current time as JSON"""
    time = get_current_time()
    return jsonify({"Current Time": time})

@app.route("/api/mem", methods=['GET'])
@limiter.limit("15 per minute")
def api_ip():
    """Return the memory stats as JSON"""
    total_ram, used_ram, total_swap, used_swap = get_memory_stats()
    return jsonify({"Total RAM": f"{total_ram:.0f}MiB",
                    "Used RAM": f"{used_ram:.0f}",
                    "Total Swap": f"{total_swap:.0f}MiB",
                    "Used Swap": f"{used_swap:.0f}"
    })

@app.route("/api/cpu", methods=['GET'])
@limiter.limit("15 per minute")
def api_cpu():
    """Return the CPU usage as JSON"""
    cpu = get_cpu_usage()
    return jsonify({"CPU Usage": cpu})

@app.route("/api/shutdown", methods=['POST'])
@limiter.limit("5 per hour")
def api_shutdown():
    """Authenticate using API key"""
    api_key = request.headers.get('x-api-key')
    if api_key == API_KEY:
        # Shut down the system
        r = subprocess.run(["sudo", "shutdown", "+1"], stdout=subprocess.PIPE, text=True)
        print(r)
        return jsonify({"message": "System shutting down in 1 minute"}), 200
    return jsonify({"error": "Unauthorized"}), 401

@app.route("/api/update", methods=['POST'])
@limiter.limit("3 per hour")
def api_update():
    """Authenticate using API key"""
    api_key = request.headers.get('x-api-key')
    if api_key == API_KEY:
        # Shut down the system
        r = subprocess.run(["sudo", "apt-get", "update"], stdout=subprocess.PIPE, text=True)
        #print(r)
        r = subprocess.run(["sudo", "apt-get", "upgrade", "-y"], stdout=subprocess.PIPE, text=True)
        #print(r)
        return jsonify({"message": "System update complete!"}), 200
    return jsonify({"error": "Unauthorized"}), 401

@app.route("/api/all", methods=['GET'])
@limiter.limit("1 per second")
def api_plain():
    """Collect system statistics and return as JSON (original endpoint /api)"""
    time = get_current_time()
    ipv4 = get_ipv4_addr()
    cpu = get_cpu_usage()
    temp = get_soc_temp()
    total_ram, used_ram, total_swap, used_swap = get_memory_stats()

    data = {
        "Current Time": time,
        "IP Address": ipv4,
        "CPU Usage": cpu,
        "SoC Temperature": temp,
        "Total RAM": f"{total_ram:.0f}MiB",
        "Used RAM": f"{used_ram:.0f}",
        "Total Swap": f"{total_swap:.0f}MiB",
        "Used Swap": f"{used_swap:.0f}"
    }

    return jsonify(data)

if __name__ == "__main__":
    # Run the Flask app
    app.run(host='localhost', port=7070)
