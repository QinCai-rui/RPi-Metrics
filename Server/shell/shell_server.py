#!/usr/bin/env python3
"""
RPi Web Shell - A simple web-based terminal for Raspberry Pi
Run this alongside your main RPi-Metrics server for isolated shell functionality
"""

import os
import pty
import select
import termios
import struct
import fcntl
import signal
import subprocess
import threading
import sys
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

# Import API_KEY from env (same as RPi-Metrics)
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import env
    API_KEY = env.API_KEY
except ImportError:
    # Fallback in case env.py doesn't exist
    API_KEY = os.getenv("API_KEY", "change-this-key")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# Store active shells
shells = {}

# Set a complete environment for shell processes
SHELL_ENV = os.environ.copy()

# Standard PATH
SHELL_ENV['PATH'] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin"
if 'PATH' in os.environ:
    SHELL_ENV['PATH'] = os.environ['PATH'] + ":" + SHELL_ENV['PATH']

# Set HOME environment variable if not already set
if 'HOME' not in SHELL_ENV:
    SHELL_ENV['HOME'] = '/root'

# Set terminal environment variables
SHELL_ENV['TERM'] = 'xterm-256color'
SHELL_ENV['SHELL'] = '/bin/bash'

@app.route('/')
def index():
    return render_template('shell.html')

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    kill_shell(request.sid)
    leave_room(request.sid)

@socketio.on('authenticate')
def handle_authenticate(data):
    client_api_key = data.get('apiKey')
    if client_api_key == API_KEY:
        join_room(request.sid)
        emit('authentication_success')
    else:
        emit('authentication_failed')

@socketio.on('create_shell')
def handle_create_shell(data):
    cols = data.get('cols', 80)
    rows = data.get('rows', 24)
    create_shell(request.sid, cols, rows)

@socketio.on('shell_input')
def handle_shell_input(data):
    success = write_to_shell(request.sid, data.get('input', ''))
    return {'success': success}

@socketio.on('resize_terminal')
def handle_resize_terminal(data):
    cols = data.get('cols', 80)
    rows = data.get('rows', 24)
    resize_terminal(request.sid, cols, rows)

def create_shell(session_id, cols=80, rows=24):
    """Create a new shell process for a session"""
    try:
        # Create a pseudo-terminal
        master, slave = pty.openpty()
        
        # Start bash with a complete environment and change to home directory
        process = subprocess.Popen(
            ['/bin/bash', '-c', 'cd ~ && exec /bin/bash'],
            preexec_fn=os.setsid,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            universal_newlines=True,
            env=SHELL_ENV
        )
        
        # Set terminal size
        fcntl.ioctl(
            master,
            termios.TIOCSWINSZ,
            struct.pack("HHHH", rows, cols, 0, 0)
        )
        
        # Store shell data
        shells[session_id] = {
            'process': process,
            'master': master,
            'slave': slave,
            'thread': None,
            'running': True
        }
        
        # Start output reader thread
        thread = threading.Thread(
            target=read_output,
            args=(session_id, master),
            daemon=True
        )
        thread.start()
        shells[session_id]['thread'] = thread
        
        return True
    except Exception as e:
        print(f"Error creating shell: {e}")
        socketio.emit('shell_error', {'error': str(e)}, room=session_id)
        return False

def resize_terminal(session_id, cols, rows):
    """Resize the terminal"""
    if session_id in shells:
        fcntl.ioctl(
            shells[session_id]['master'],
            termios.TIOCSWINSZ,
            struct.pack("HHHH", rows, cols, 0, 0)
        )
        return True
    return False

def write_to_shell(session_id, data):
    """Write data to the shell"""
    if session_id in shells:
        try:
            os.write(shells[session_id]['master'], data.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Error writing to shell: {e}")
            return False
    return False

def read_output(session_id, fd):
    """Read output from the shell and emit it via socketio"""
    max_read_bytes = 1024 * 20
    
    while session_id in shells and shells[session_id]['running']:
        try:
            r, _, _ = select.select([fd], [], [], 0.1)
            if r:
                output = os.read(fd, max_read_bytes)
                
                if output:
                    # Convert bytes to string safely
                    text = output.decode('utf-8', errors='replace')
                    socketio.emit('shell_output', {'output': text}, room=session_id)
                else:
                    # EOF on the file descriptor
                    kill_shell(session_id)
                    break
            
            # Short sleep to prevent high CPU usage
            time.sleep(0.01)
        except Exception as e:
            print(f"Error reading from shell: {e}")
            socketio.emit('shell_error', {'error': str(e)}, room=session_id)
            kill_shell(session_id)
            break

def kill_shell(session_id):
    """Kill a shell process"""
    if session_id in shells:
        shells[session_id]['running'] = False
        
        # Kill the process
        try:
            os.killpg(os.getpgid(shells[session_id]['process'].pid), signal.SIGTERM)
        except:
            pass
        
        # Close file descriptors
        try:
            os.close(shells[session_id]['master'])
        except:
            pass
        
        try:
            os.close(shells[session_id]['slave'])
        except:
            pass
        
        # Remove from shells dictionary
        del shells[session_id]
        
        return True
    return False

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    # Run on port 5001 by default so it doesn't conflict with RPi-Metrics
    port = int(os.getenv("SHELL_PORT", 5001))
    print(f"Starting RPi Web Shell on port {port}")
    
    # The important change: allow unsafe werkzeug
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
