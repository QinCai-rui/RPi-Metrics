from flask import Flask, jsonify
import datetime
import subprocess

app = Flask(__name__)

def get_current_time():
    timeStr = datetime.datetime.now().strftime("%b %d %H:%M:%S")
    return timeStr

def get_ipv4_addr():
    # Run `hostname -I` and capture output
    result = subprocess.run(["hostname", "-I"], stdout=subprocess.PIPE, text=True)
    ipaddr = result.stdout.strip()
    return ipaddr

def get_cpu_usage():
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
    # Run `vcgencmd measure_temp` and capture output
    result = subprocess.run(["vcgencmd", "measure_temp"], stdout=subprocess.PIPE, text=True)
    cpuTemp = result.stdout.strip().replace("temp=", "").replace("'C", "C")
    return cpuTemp

def get_memory_stats():
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
def root():
    # Root webpage
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
    app.run(host='localhost', port=7070)
