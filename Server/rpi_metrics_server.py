from flask import Flask, jsonify, request, render_template, redirect
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

def get_commit_info():
    """Read the commit information"""
    result = subprocess.run(["bash", "/usr/share/rpi-metrics/Server/get_commit_info.sh"], stdout=subprocess.PIPE, text=True)
    global commit_id, commit_time
    with open('/usr/share/rpi-metrics/commit_info.txt') as f:
        lines = f.readlines()
        commit_id = lines[0].strip().split(': ')[1]
        commit_time = lines[1].strip().split(': ')[1]

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

def get_disk_info():
    """Function to get disk usage statistics"""
    result = subprocess.run(["df", "-h", "/"], stdout=subprocess.PIPE, text=True)
    lines = result.stdout.strip().split('\n')
    parts = lines[1].split()
    
    return {
        "Total Space": parts[1],
        "Used Space": parts[2],
        "Available Space": parts[3],
        "Usage Percentage": parts[4]
    }

def get_system_info():
    """Function to get system information"""
    model_result = subprocess.run(["cat", "/proc/device-tree/model"], stdout=subprocess.PIPE, text=True)
    kernel_result = subprocess.run(["uname", "-r"], stdout=subprocess.PIPE, text=True)
    os_result = subprocess.run(["cat", "/etc/os-release"], stdout=subprocess.PIPE, text=True)
    
    # Parse OS release info
    os_info = {}
    for line in os_result.stdout.strip().split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            os_info[key] = value.strip('"')
    
    return {
        "Model": model_result.stdout.strip().replace('\x00', ''),
        "Kernel Version": kernel_result.stdout.strip(),
        "OS": os_info.get('PRETTY_NAME', 'Unknown')
    }

def get_uptime_info():
    """Function to get system uptime"""
    result = subprocess.run(["uptime", "-p"], stdout=subprocess.PIPE, text=True)
    return result.stdout.strip()

@app.route("/")
@limiter.limit("2 per 3 seconds")
def index():
    """Render the main HTML page"""
    return render_template('index.html', commit_id=commit_id, commit_time=commit_time)

@app.route("/api", methods=['GET'])
@limiter.limit("1 per second")
def api():
    """Handles undefined subdirectory in API calls"""
    return {
        "Error": "404 Not Found. Please see Documentation",
        "Available Endpoints": {
            "/api/time": "Get current server time",
            "/api/mem": "Get memory statistics",
            "/api/cpu": "Get CPU usage",
            "/api/disk": "Get disk usage statistics",
            "/api/uptime": "Get system uptime",
            "/api/system": "Get system information",
            "/api/shutdown": "Authorize shutdown",
            "/api/reboot": "Authorize system reboot",
            "/api/update": "Authorize system update",
            "/api/all": "Get all system statistics"
        },
        "Documentation": "https://github.com/qincai-rui/rpi-metrics#available-api-endpoints"
    }, 404

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
    temp = get_soc_temp()
    return jsonify({"CPU Usage": cpu,
                    "SoC Temperature": temp
    })

@app.route("/api/disk", methods=['GET'])
@limiter.limit("5 per minute")
def api_disk():
    """Return disk usage statistics as JSON"""
    return jsonify(get_disk_info())

@app.route("/api/uptime", methods=['GET'])
@limiter.limit("5 per minute")
def api_uptime():
    """Return system uptime as JSON"""
    uptime = get_uptime_info()
    return jsonify({"System Uptime": uptime})

@app.route("/api/system", methods=['GET'])
@limiter.limit("2 per minute")
def api_system():
    """Return system information as JSON"""
    return jsonify(get_system_info())

@app.route("/api/shutdown", methods=['POST'])
@limiter.limit("5 per hour")
def api_shutdown():
    """Authenticate using API key"""
    api_key = request.headers.get('x-api-key')
    if api_key == API_KEY:
        # Shut down the system
        r = subprocess.run(["shutdown", "+1"], stdout=subprocess.PIPE, text=True)
        print(r)
        return jsonify({"message": "System shutting down in 1 minute"}), 200
    return jsonify({"error": "Unauthorized"}), 401

@app.route("/api/reboot", methods=['POST'])
@limiter.limit("5 per hour")
def api_reboot():
    """Authenticate using API key and reboot the system"""
    api_key = request.headers.get('x-api-key')
    if api_key == API_KEY:
        r = subprocess.run(["reboot"], stdout=subprocess.PIPE, text=True)
        return jsonify({"message": "System rebooting now"}), 200
    return jsonify({"error": "Unauthorized"}), 401

@app.route("/api/update", methods=['POST'])
@limiter.limit("3 per hour")
def api_update():
    """Authenticate using API key"""
    api_key = request.headers.get('x-api-key')
    if api_key == API_KEY:
        # Shut down the system
        r = subprocess.run(["apt-get", "update"], stdout=subprocess.PIPE, text=True)
        #print(r)
        r = subprocess.run(["apt-get", "full-upgrade", "-y"], stdout=subprocess.PIPE, text=True)
        #print(r)
        return jsonify({"message": "System update complete!"}), 200
    return jsonify({"error": "Unauthorized"}), 401

@app.route("/api/all", methods=['GET'])
@limiter.limit("1 per second")
def api_plain():
    """Collect system statistics and return as JSON (original endpoint /api)"""
    # Use existing functions for all metrics (just to DRY)
    time = get_current_time()
    ipv4 = get_ipv4_addr()
    cpu = get_cpu_usage()
    temp = get_soc_temp()
    total_ram, used_ram, total_swap, used_swap = get_memory_stats()
    disk_info = get_disk_info()
    uptime = get_uptime_info()
    system_info = get_system_info()

    data = {
        "Current Time": time,
        "IP Address": ipv4,
        "CPU Usage": cpu,
        "SoC Temperature": temp,
        "Total RAM": f"{total_ram:.0f}MiB",
        "Used RAM": f"{used_ram:.0f}",
        "Total Swap": f"{total_swap:.0f}MiB",
        "Used Swap": f"{used_swap:.0f}",
        "System Uptime": uptime,
        "Disk Total": disk_info["Total Space"],
        "Disk Used": disk_info["Used Space"],
        "Disk Available": disk_info["Available Space"],
        "Disk Usage": disk_info["Usage Percentage"],
        "System Model": system_info["Model"],
        "Kernel Version": system_info["Kernel Version"],
        "OS": system_info["OS"]
    }

    return jsonify(data)

@app.route("/docs", methods=['GET'])
def docs():
    """Redirect to the GitHub documentation"""
    return redirect("https://github.com/QinCai-rui/RPi-Metrics#rpi-metrics")

if __name__ == "__main__":
    get_commit_info()
    # Run the Flask app
    app.run(host='0.0.0.0', port=7070)
