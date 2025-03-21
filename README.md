# RPi Metrics

<p align="center">
  <img alt="Github top language" src="https://img.shields.io/github/languages/top/qincai-rui/rpi-metrics?color=56BEB8">

  <img alt="Github language count" src="https://img.shields.io/github/languages/count/qincai-rui/rpi-metrics?color=56BEB8">

  <img alt="Repository size" src="https://img.shields.io/github/repo-size/qincai-rui/rpi-metrics?color=56BEB8">

  <img alt="License" src="https://img.shields.io/github/license/qincai-rui/rpi-metrics?color=56BEB8">

  <!-- <img alt="Github issues" src="https://img.shields.io/github/issues/qincai-rui/rpi-metrics?color=56BEB8" /> -->

  <!-- <img alt="Github forks" src="https://img.shields.io/github/forks/qincai-rui/rpi-metrics?color=56BEB8" /> -->

  <!-- <img alt="Github stars" src="https://img.shields.io/github/stars/qincai-rui/rpi-metrics?color=56BEB8" /> -->
</p>

Welcome to the **RPi Metrics** project! This project allows you to monitor and manage your Raspberry Pi's system metrics such as CPU usage, memory usage, and more via a Flask server and a client application (optional but highly recommended).

> [!TIP]
> You can also _**remote poweroff**_, _**remote reboot**_, and _**remote update**_ your Pi, from anywhere in the world, provided that the server is reachable from the wider internet. (Check out <https://pi5-monitor.qincai.xyz> to see it yourself!)

## Prerequisites

Ensure you have the following installed on your Raspberry Pi:
If you don't have everything, no worries! Just use the [installation script below](#quick-installation)! It will handle everything for you!

- Python 3
- Pip
- Git
- Curl

**However, ensure that curl is already installed on your system before using the Quick Installer.**

## Quick Installation

Use the installation script by running:

```sh
sudo su
bash <(curl -sSL https://qincai.xyz/rpi-metrics-installer.sh)
```

Alternatively, you can run:

```sh
curl -sSL https://qincai.xyz/rpi-metrics-installer.sh | sudo bash -s - -y
```

to accept all defaults.

Or:

```sh
curl -sSL https://qincai.xyz/rpi-metrics-installer.sh | bash -s - --no-check-root
```

to bypass root check.

## Setting Up the Server

> [!NOTE]
> You can skip this if you used the [Quick Installer script](#quick-installation).

1. **Clone this repository**

    ```sh
    sudo git -c http.followRedirects=true clone https://github.com/QinCai-rui/RPi-Metrics.git /usr/share/rpi-metrics
    ```

2. **Navigate to the server directory:**

    ```sh
    cd /usr/share/rpi-metrics/Server
    ```

3. **Activate the virtual environment:**

    ```sh
    source venv/bin/activate
    ```

4. **Run the server:**

    ```sh
    sudo python3 rpi_metrics_server.py
    ```

5. **Alternatively, start it as a systemd service (_Recommended_):**

    ```sh
    sudo cp /usr/share/rpi-metrics/Server/rpi-metricsd.service /etc/systemd/system/
    sudo systemctl enable --now rpi-metricsd
    ```

## Setting Up the Client

The client should be a Raspberry Pi Pico W or Pico 2 W with 2 buttons and an SSD1306 128x64 screen. The Pico is optional. You can use this API on any device.

1. **Create a .env file in the client directory with the following content:**

    ```env
    SSID = "your_wifi_ssid"
    PSK = "your_wifi_password"
    SERVER_URL = "http://your_server_url"
    API_KEY = "your_api_key_here"
    ```

2. **Download the client code to your Pi Pico.**
The code is [here](https://github.com/QinCai-rui/RPi-Metrics/blob/main/Client/rpi_metrics_client.py).
3. **Ensure your Raspberry Pi Pico is connected to the internet.**

4. **Run the client script** (or save it as `main.py` to run at startup).

## Available API Endpoints

- **GET /api/time**: Retrieve the current system time.
_Example Output:_

    ```json
    {
      "Current Time":"Jan 01 00:00:00"
    }
    ```

<br>

- **GET /api/mem**: Retrieve memory statistics.
_Example Output:_

    ```json
    {
      "Total RAM": "465MiB",
      "Total Swap": "2048MiB",
      "Used RAM": "244",
      "Used Swap": "72"
    }
    ```

<br>

- **GET /api/cpu**: Retrieve CPU usage.
_Example Output:_

    ```json
    {
      "CPU Usage": "31%",
      "SoC Temperature": "48.9C"
    }
    ```

<br>

- **GET /api/disk**: Retrieve disk usage statistics. Example Output:

    ```json
    {
      "Total Space": "32G",
      "Used Space": "12G",
      "Available Space": "18G",
      "Usage Percentage": "41%"
    }
    ```
    
<br>

- **GET /api/system**: Retrieve detailed system information. Example Output:
  
    ```json
    {
      "Model": "Raspberry Pi 5 Model B Rev 1.0",
      "Kernel Version": "6.6.74+rpt-rpi-2712",
      "OS": "Debian GNU/Linux trixie/sid"
    }
    ```
    
<br>

- **POST /api/shutdown**: Shutdown the system (requires API key in the header). Header name should be `x-api-key`. The server returns `HTTP 200` and the following if a valid API key is provided:

    ```json
    {
        "message": "System shutting down"
    }
    ```

    If a valid API key is not provided, the server returns `HTTP 401` and the following:

    ```json
    {
        "error": "Unauthorized"
    }   
    ```

    _Example Usage:_

    ```sh
    curl -L -X POST http://your_server_url/api/shutdown -H "x-api-key: your_api_key_here"
    ```

<br>

- **POST /api/reboot**: Reboot the system (requires API key in the header). The server returns HTTP 200 and the following if a valid API key is provided:
  
    ```json
    {
        "message": "System rebooting now"
    }
    ```

    If a valid API key is not provided, the server returns HTTP 401.

    _Example Usage:_

    ```sh
    curl -L -X POST http://your_server_url/api/reboot -H "x-api-key: your_api_key_here"
    ```
    
<br>

- **POST /api/update**: Update the system (requires API key in the header). Header name should be `x-api-key`. The server returns `HTTP 200` and the following if a valid API key is provided, after a update:

    ```json
    {
        "message": "System update complete!"
    }
    ```

    If a valid API key is not provided, the server returns `HTTP 401` and the following:

    ```json
    {
        "error": "Unauthorized"
    }   
    ```

    _Example Usage:_

    ```sh
    curl -L -X POST http://your_server_url/api/update -H "x-api-key: your_api_key_here"
    ```

<br>

- **GET /api/all**: Retrieve comprehensive system statistics.
_Example Output:_

    ```json
    {
      "CPU Usage": "31%",
      "Current Time": "Jan 1 00:00:00",
      "IP Address": "192.168.2.123 100.93.81.48 fd7a:115c:a1e0::8c01:5130",
      "SoC Temperature": "48.9C",
      "Total RAM": "465MiB",
      "Total Swap": "2048MiB",
      "Used RAM": "244",
      "Used Swap": "72"
    }
    ```

<br>

- **GET /**: Access the user-friendly GUI.
_Example Output:_
![root GUI output image](https://cloud-lx3yiwapy-hack-club-bot.vercel.app/0image.png)

## Uninstallation
If for any reason, you want to uninstall the RPi Metrics server from your Raspberry Pi, use `rpi-metrics-uninstall` to uninstall it. If that command is not found, try this if you only want to uninstall this project, Python excluded:

```sh
curl -sSL https://qincai.xyz/rpi-metrics-uninstaller.sh | sudo bash -s - -wet
```

Use this if you want to remove Python and other packages installed as well:

```sh
curl -sSL https://qincai.xyz/rpi-metrics-uninstaller.sh | sudo bash -s - -extra-wet
```

> [!WARNING]
> Passing the `--extra-wet` flag will remove `python3`, `python3-pip`, and `python3-venv` from your system. USE WITH CAUTION!!

## Contributing

Contributions are welcome! Please create an issue or fork the repository and submit a pull request for review.

## License

This project is licensed under the GPLv3 License. See the [LICENSE](LICENSE) file for details.
