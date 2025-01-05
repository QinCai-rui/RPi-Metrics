#!/bin/bash
# This script took inspiration from the Pi-Hole and RaspAP installer script.
# Created with love by QinCai with assistance from Copilot
# ASCII art generated by https://patorjk.com/software/taag/
# MAKE SURE THAT YOU HAVE DOWNLOADED THIS SCRIPT FROM A TRUST-WORTHY SOURCE!!!

#########################################################
#                   Not working??                       #
#                                                       #
#  Try running these, one after another:                #
#   $ wget https://qincai.xyz/rpi-metrics-installer.sh  #
#   $ chmod +x rpi-metrics-installer.sh                 #
#   $ sudo ./rpi-metrics-installer.sh`                  #
#########################################################

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
MAGENTA='\033[1;35m'
CYAN='\033[1;36m'
NC='\033[0m' # No Color

AUTO_CONFIRM=false

confirm() {
    if [ "$AUTO_CONFIRM" = true ]; then
        return 0
    fi

    read -r -p "$1 [y/n]: " yn
    case $yn in
        [Yy]* ) return 0;;
        [Nn]* ) echo -e "${RED}Installation aborted.${NC}"; exit 1;;
        * ) echo -e "${YELLOW}Please answer yes or no.${NC}";;
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

log_info() {
    echo -e "${BLUE}[ℹ] $1${NC}"
}

log_warning() {
    echo -e "${MAGENTA}[⚠] $1${NC}"
}

check_root() {
    log_info "Checking for root privileges..."
    if [ "$EUID" -ne 0 ]; then
        log_failure "Please run as root."
        exit 1
    else
        log_success "Running as root."
    fi
}

check_rpi() {
    log_info "Checking if running on a Raspberry Pi..."
    if grep -q "Raspberry Pi" /proc/cpuinfo; then
        log_success "Running on a Raspberry Pi."
    else
        log_failure "This script can only be run on a Raspberry Pi."
        exit 1
    fi
}

check_curl() {
    log_info "Checking for curl..."
    if ! command -v curl -sL example.com &> /dev/null; then
        log_failure "curl could not be found."
        confirm "Install curl?"
        sudo apt update && sudo apt install -y curl
        log_success "curl installed!"
    else
        log_success "curl is already installed."
    fi
}

main() {
    echo "  _____   _____  _   __  __        _          _            "
    echo " |  __ \ |  __ \(_) |  \/  |      | |        (_)           "
    echo " | |__) || |__) |_  | \  / |  ___ | |_  _ __  _   ___  ___ "
    echo " |  _  / |  ___/| | | |\/| | / _ \| __|| '__|| | / __|/ __|"
    echo " | | \ \ | |    | | | |  | ||  __/| |_ | |   | || (__ \__ \\"
    echo " |_|  \_\|_|    |_| |_|  |_| \___| \__||_|   |_| \___||___/"
    echo "                                                           "
    echo -e "${CYAN}Welcome to the RPi Metrics installation script!${NC}"
    echo "Make sure that you have downloaded this script from a trustworthy source!!"
    echo ""
    echo "${BLUE}"
    echo "#########################################################"
    echo "#                   Not working??                       #"
    echo "#                                                       #"
    echo "#  Try running these, one after another:                #"
    echo "#   \$ wget https://qincai.xyz/rpi-metrics-installer.sh #"
    echo "#   \$ chmod +x rpi-metrics-installer.sh                #"
    echo "#   \$ sudo ./rpi-metrics-installer.sh                  #"
    echo "#########################################################"
    echo "${NC}"


    check_root

    check_rpi

    check_curl

    confirm "Update your package list and install necessary packages?"

    log_info "Updating package list and installing necessary packages..."
    # Update package list and install necessary packages
    if sudo apt update && sudo apt install -y python3 python3-pip python3-venv; then
        log_success "Package list updated and necessary packages installed."
    else
        log_failure "Failed to update package list or install necessary packages."
        exit 1
    fi

    confirm "Create a directory for rpi-metrics in /usr/share?"

    log_info "Creating directory for rpi-metrics..."
    # Create a directory for rpi-metrics
    if sudo mkdir -p /usr/share/rpi-metrics && cd /usr/share/rpi-metrics; then
        log_success "Directory for rpi-metrics created in /usr/share."
    else
        log_failure "Failed to create directory for rpi-metrics."
        exit 1
    fi

    confirm "Set up a virtual environment in /usr/share/rpi-metrics?"

    log_info "Setting up virtual environment..."
    # Set up a virtual environment and activate it
    if sudo python3 -m venv venv && source venv/bin/activate; then
        log_success "Virtual environment set up and activated in /usr/share/rpi-metrics."
    else
        log_failure "Failed to set up virtual environment."
        exit 1
    fi

    confirm "Install Flask in the virtual environment?"

    log_info "Installing Flask in the virtual environment..."
    # Install Flask
    if sudo venv/bin/pip install Flask; then
        log_success "Flask installed in the virtual environment."
    else
        log_failure "Failed to install Flask."
        exit 1
    fi

    confirm "Download the RPi-Metrics server file from GitHub?"

    log_info "Downloading the RPi-Metrics server file from GitHub..."
    # Download the rpi-metrics server file
    http_status=$(sudo curl -L -w "%{http_code}" -o rpi_metrics.py -s https://qincai.xyz/rpi-metrics-server.py)

    if [ "$http_status" -eq 200 ] || [ "$http_status" -eq 301]; then
        log_success "rpi-metrics server file downloaded successfully."
    elif [ "$http_status" -eq 404 ]; then
        log_failure "Failed to download rpi-metrics server file: 404 Not Found."
        exit 1
    else
        log_failure "Failed to download rpi-metrics server file: HTTP status code $http_status."
        exit 1
    fi

    confirm "Deactivate the virtual environment?"

    log_info "Deactivating the virtual environment..."
    # Deactivate the virtual environment
    if deactivate; then
        log_success "Virtual environment deactivated."
    else
        log_failure "Failed to deactivate the virtual environment."
        exit 1
    fi

    confirm "Download the systemd service file for rpi-metrics from GitHub?"

    log_info "Downloading the systemd service file for rpi-metrics from GitHub..."
    # Download the systemd service file
    http_status=$(sudo curl -L -w "%{http_code}" -o /etc/systemd/system/rpi-metricsd.service -s https://qincai.xyz/rpi-metrics.service)

    if [ "$http_status" -eq 200] || [ "$http_status" -eq 301]; then
        log_success "Systemd service file downloaded successfully."
    elif [ "$http_status" -eq 404]; then
        log_failure "Failed to download systemd service file: 404 Not Found."
        exit 1
    else
        log_failure "Failed to download systemd service file: HTTP status code $http_status."
        exit 1
    fi

    log_info "Reloading systemd daemon..."
    # Reload systemd daemon
    if sudo systemctl daemon-reload; then
        log_success "Systemd daemon reloaded."
    else
        log_failure "Failed to reload systemd daemon."
        exit 1
    fi

    confirm "Start and enable the rpi-metricsd service?"

    log_info "Starting and enabling the rpi-metricsd service..."
    # Start and enable the rpi-metricsd service
    if sudo systemctl start rpi-metricsd && sudo systemctl enable rpi-metricsd; then
        log_success "rpi-metricsd service started and enabled."
    else
        log_failure "Failed to start or enable rpi-metricsd service."
        exit 1
    fi

    echo -e "${GREEN}RPi Metrics installation completed!${NC}"
}

# Call the main function
main "$@"
