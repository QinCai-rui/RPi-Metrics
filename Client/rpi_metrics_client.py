import network
import urequests as requests
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import time
import env

# Define Wi-Fi credentials (in your env.py file)
SSID = env.SSID
PASSWORD = env.PSK

SERVER_URL = f"{env.SERVER_URL}/api/all"
SHUTDOWN_URL = f"{env.SERVER_URL}/api/shutdown"
UPDATE_URL = f"{env.SERVER_URL}/api/update"

TIME_INTERVAL = 0.5   # Wait time between requests
API_KEY = env.API_KEY  # Store your API key in the env.py file. See README for more info

# Initialise the display
i2c = I2C(0, scl=Pin(17), sda=Pin(16))
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# Define pins for buttons
LEFT_BUTTON = Pin(0, Pin.IN, Pin.PULL_UP)
RIGHT_BUTTON = Pin(11, Pin.IN, Pin.PULL_UP)

def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    print('Connecting to WiFi...', end='')
    OLED.fill(0)
    OLED.text('Awaiting network', 0, 0)
    OLED.show()

    while not wlan.isconnected():
        print('.', end='')
        time.sleep(1)
    print('Connected!')
    OLED.fill(0)
    OLED.text('Connected!', 0, 0)
    OLED.show()
    print(wlan.ifconfig())

def fetch_data():
    """Fetch data from the Flask server"""
    global response
    try:
        response = requests.get(SERVER_URL)
        if response.status_code != 200:
            print(f"HTTP Error: {response.status_code} - {response.text}")
            OLED.fill(0)
            OLED.text(f"HTTP {response.status_code}", 0, 0)
            OLED.text(response.text, 0, 12)
            OLED.show()
            return None
        return response.json()
    except OSError as e:
        print(f"Connection Error: {e}")
        OLED.fill(0)
        OLED.text("Conn Err", 0, 0)
        OLED.show()
        time.sleep(2)
        return None
    except ValueError as e:
        print(f"JSON Error: {e}")
        OLED.fill(0)
        OLED.text("Invalid JSON", 0, 0)
        OLED.show()
        return None
    except Exception as e:
        print(f"Unknown Error: {e}")
        OLED.fill(0)
        OLED.text("Unknown Error", 0, 0)
        OLED.show()
        return None

def send_shutdown_request():
    """Send shutdown request to the Flask server with authentication"""
    OLED.fill(0)
    OLED.text("Sending shutdown", 0, 0)
    OLED.text("request...", 0, 12)
    OLED.show()
    try:
        headers = {'x-api-key': API_KEY}
        response = requests.post(SHUTDOWN_URL, headers=headers)
        if response.status_code == 200:
            print("Shutdown request sent successfully")
            OLED.fill(0)
            OLED.text("Server shutting", 0, 0)
            OLED.text("down in 1 min", 0, 12)
        else:
            print(f"Failed to send shutdown request: HTTP {response.status_code} - {response.text}")
            OLED.fill(0)
            OLED.text(f"FAILED: HTTP {response.status_code}", 0, 0)
            OLED.text(response.text, 0, 12)
    except Exception as e:
        print(f"Error sending shutdown request: {e}")
        OLED.fill(0)
        OLED.text("Error occurred", 0, 0)
        OLED.text("when sending req", 0 ,12)
    finally:
        OLED.show()

def send_update_request():
    """Send update request to the Flask server with authentication"""
    OLED.fill(0)
    OLED.text("Sending update", 0, 0)
    OLED.text("request...", 0, 12)
    OLED.text("This might take", 0, 36)
    OLED.text("a long time...", 0, 48)
    OLED.show()
    try:
        headers = {'x-api-key': API_KEY}
        response = requests.post(SHUTDOWN_URL, headers=headers)
        if response.status_code == 200:
            print("Update request sent successfully")
            OLED.fill(0)
            OLED.text("Server is", 0, 0)
            OLED.text("updating...", 0, 12)
        else:
            print(f"Failed to send update request: HTTP {response.status_code} - {response.text}")
            OLED.fill(0)
            OLED.text(f"FAILED: HTTP {response.status_code}", 0, 0)
            OLED.text(response.text, 0, 12)
    except Exception as e:
        print(f"Error sending update request: {e}")
        OLED.fill(0)
        OLED.text("Error occurred", 0, 0)
        OLED.text("when sending req", 0 ,12)
    finally:
        OLED.show()

def display_data(data):
    """Display data on the OLED screen"""
    OLED.fill(0)
    if data:
        OLED.text(f"{data['Current Time']}", 0, 0)  # Date and time
        OLED.text(f"{data['IP Address']}", 0, 12)  # IP address
        OLED.text(f"CPU: {data['CPU Usage']} {data['SoC Temperature']}", 0, 26)  # CPU and temp
        OLED.text(f"RAM: {data['Used RAM']}/{data['Total RAM']}", 0, 38)  # RAM
        OLED.text(f"VM: {data['Used Swap']}/{data['Total Swap']}", 0, 50)  # Swap
    elif response.status_code != 200:
        OLED.text(f"HTTP {response.status_code}", 0, 0)
        OLED.text(response.text, 0, 12)
    else:
        OLED.text("Error while", 0, 0)
        OLED.text("fetching data", 0, 12)
    OLED.show()
    time.sleep(2)

def main():
    connect_wifi(SSID, PASSWORD)
    while True:
        try:
            data = fetch_data()
            display_data(data)
            if not LEFT_BUTTON.value():
                send_shutdown_request()
                time.sleep(2)  # Add a delay to avoid multiple requests
            if not RIGHT_BUTTON.value():
                send_update_request()
                time.sleep(2)
        except Exception as e:
            print(f"Error in main loop: {e}")
            OLED.fill(0)
            OLED.text("Err Occurred", 0, 0)
            OLED.show()
        time.sleep(TIME_INTERVAL)

if __name__ == "__main__":
    main()
