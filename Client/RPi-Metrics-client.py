import network
import urequests as requests
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import time

# Define Wi-Fi credentials
SSID = 'SSID'
PASSWORD = 'Password'

# Initialise the display
i2c = I2C(0, scl=Pin(17), sda=Pin(16))
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    print('Connecting to WiFi...', end='')
    oled.fill(0)
    oled.text('Awaiting network', 0, 0)
    oled.show()
    
    while not wlan.isconnected():
        print('.', end='')
        time.sleep(1)
    print('Connected!')
    oled.fill(0)
    oled.text('Connected!', 0, 0)
    oled.show()
    print(wlan.ifconfig())

# Fetch data from the Flask server
def fetch_data():
    try:
        global response
        response = requests.get('https://pi-monitor.qincai.xyz')
        if response.status_code != 200:
            #oled.fill(0)
            #oled.text(f"HTTP {response.status_code}", 0, 0)
            #oled.show()
            return None
        return response.json()
    except OSError as e:
        oled.fill(0)
        oled.text("Conn Err", 0, 0)
        oled.show()
        return None
    except ValueError:
        oled.fill(0)
        oled.text("Invalid JSON", 0, 0)
        oled.show()
        return None

# Display data on the OLED screen
def display_data(data):
    oled.fill(0)  # Clear the display
    if data:
        oled.text(f"{data['Current Time']}", 0, 0)  # Date and time
        #oled.text(f"{data['IP Address']}", 0, 12)  # IP address
        oled.text(f"CPU: {data['CPU Usage']} {data['SoC Temperature']}", 0, 24)  # CPU and temperature
        oled.text(f"RAM: {data['Used RAM']}/{data['Total RAM']}", 0, 36)  # RAM
        oled.text(f"VM: {data['Used Swap']}/{data['Total Swap']}", 0, 48)  # Swap
    elif response.status_code != 200:
        oled.text(f"HTTP {response.status_code}", 0, 0)
    else:
        oled.text("No Data", 0, 0)
    oled.show()

# Main loop
def main():
    connect_wifi(SSID, PASSWORD)
    
    while True:
        try:
            data = fetch_data()
            display_data(data)
        except Exception as e:
            print(e)
            oled.fill(0)
            oled.text("Err Occurred", 0, 0)
            oled.show()
        time.sleep(3)

if __name__ == "__main__":
    main()

