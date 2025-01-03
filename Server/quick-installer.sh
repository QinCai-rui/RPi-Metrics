#!/bin/bash
# This script took inspiration from the Pi-Hole and RaspAP installer script.
# Created with love by QinCai with assistance from Copilot
# ASCII art generated by https://patorjk.com/software/taag/
# MAKE SURE YOU DOWNLOADED THIS SCRIPT FROM A TRUST-WORTHY SOURCE!!!

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

AUTO_CONFIRM=false

confirm() {
    if [ "$AUTO_CONFIRM" = true ]; then
        return 0
    fi

    read -r -p "$1 [y/n]: " yn
    case $yn in
        [Yy]* ) return 0;;
        [Nn]* ) echo "Installation aborted."; exit 1;;
        * ) echo "Please answer yes or no.";;
    esac
}

if [ "$1" = "-y" ]; then
    AUTO_CONFIRM=true
fi

log_success() {
    echo -e "${GREEN}[✔] $1${NC}"
}

log_failure() {
    echo -e "${RED}[✘] $1${NC}"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_failure "Please run as root."
        exit 1
    fi
}

check_curl() {
    if ! command -v curl &> /dev/null; then
        log_failure "curl could not be found."
        confirm "Install curl?"
        sudo apt update && sudo apt install -y curl
        log_success "curl installed!"
    else
        log_success "curl is already installed."
    fi
}

main() {
    echo "Starting main function..."

    echo "  _____   _____  _   __  __        _          _            "
    echo " |  __ \ |  __ \(_) |  \/  |      | |        (_)           "
    echo " | |__) || |__) |_  | \  / |  ___ | |_  _ __  _   ___  ___ "
    echo " |  _  / |  ___/| | | |\/| | / _ \| __|| '__|| | / __|/ __|"
    echo " | | \ \ | |    | | | |  | ||  __/| |_ | |   | || (__ \__ \\"
    echo " |_|  \_\|_|    |_| |_|  |_| \___| \__||_|   |_| \___||___/"
    echo "                                                           "
    echo "Welcome to the RPi Metrics installation script!"
    echo "Make sure you downloaded this script from a trustworthy source!!"

    # Check for root privileges
    check_root

    # Check and install curl if necessary
    check_curl

    # Confirm to proceed
    confirm "Update your package list and install necessary packages?"

    # Update package list and install necessary packages
    if sudo apt update && sudo apt install -y python3 python3-pip python3-venv; then
        log_success "Package list updated and necessary packages installed."
    else
        log_failure "Failed to update package list or install necessary packages."
        exit 1
    fi

    # Confirm to create the directory
    confirm "Create a directory for rpi-metrics in /usr/share?"

    # Create a directory for rpi-metrics
    if sudo mkdir -p /usr/share/rpi-metrics && cd /usr/share/rpi-metrics; then
        log_success "Directory for rpi-metrics created in /usr/share."
    else
        log_failure "Failed to create directory for rpi-metrics."
        exit 1
    fi

    # Confirm to set up a virtual environment
    confirm "Set up a virtual environment in /usr/share/rpi-metrics?"

    # Set up a virtual environment and activate it
    if sudo python3 -m venv venv && source venv/bin/activate; then
        log_success "Virtual environment set up and activated in /usr/share/rpi-metrics."
    else
        log_failure "Failed to set up virtual environment."
        exit 1
    fi

    # Confirm to install Flask
    confirm "Install Flask in the virtual environment?"

    # Install Flask
    if sudo venv/bin/pip install Flask; then
        log_success "Flask installed in the virtual environment."
    else
        log_failure "Failed to install Flask."
        exit 1
    fi

    # Confirm to download the server file
    confirm "Download the RPi-Metrics server file from GitHub?"

    # Download the rpi-metrics server file
    http_status=$(sudo curl -L -w "%{http_code}" -o rpi_metrics.py -s https://qincai.xyz/rpi-metrics-server.py)

    if [ "$http_status" -eq 200 ] || [ "$http_status" -eq 301 ]; then
        log_success "rpi-metrics server file downloaded successfully."
    elif [ "$http_status" -eq 404 ]; then
        log_failure "Failed to download rpi-metrics server file: 404 Not Found."
        exit 1
    else
        log_failure "Failed to download rpi-metrics server file: HTTP status code $http_status."
        exit 1
    fi

    # Confirm to deactivate the virtual environment
    confirm "Deactivate the virtual environment?"

    # Deactivate the virtual environment
    if deactivate; then
        log_success "Virtual environment deactivated."
    else
        log_failure "Failed to deactivate the virtual environment."
        exit 1
    fi

    # Confirm to download the systemd service file
    confirm "Download the systemd service file for rpi-metrics from GitHub?"

    # Download the systemd service file
    http_status=$(sudo curl -L -w "%{http_code}" -o /etc/systemd/system/rpi-metricsd.service -s https://qincai.xyz/rpi-metrics.service)

    if [ "$http_status" -eq 200 ] || [ "$http_status" -eq 301 ]; then
        log_success "Systemd service file downloaded successfully."
    elif [ "$http_status" -eq 404 ]; then
        log_failure "Failed to download systemd service file: 404 Not Found."
        exit 1
    else
        log_failure "Failed to download systemd service file: HTTP status code $http_status."
        exit 1
    fi

    # Reload systemd daemon
    if sudo systemctl daemon-reload; then
        log_success "Systemd daemon reloaded."
    else
        log_failure "Failed to reload systemd daemon."
        exit 1
    fi

    # Confirm to start and enable the service
    confirm "Start and enable the rpi-metricsd service?"

    # Start and enable the rpi-metricsd service
    if sudo systemctl start rpi-metricsd && sudo systemctl enable rpi-metricsd; then
        log_success "rpi-metricsd service started and enabled."
    else
        log_failure "Failed to start or enable rpi-metricsd service."
        exit 1
    fi

    echo "RPi Metrics installation completed!"
}

# Call the main function
main "$@"
