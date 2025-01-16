#!/bin/bash
# Uninstallation script for RPi Metrics
# Created with love by QinCai with assistance from Copilot (the colours)
# This script provides two options for uninstallation:
# --wet: Standard uninstallation without removing Python packages.
# --extra-wet: Full uninstallation including removal of Python packages.

set -e

# Colours for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Colour

REMOVE_PYTHON_PACKAGES=false

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

main() {
    clear
    echo "Starting RPi Metrics uninstallation..."
    sleep 0.5
    echo -e "${CYAN}  _____   _____  _   __  __        _          _            "
    sleep 0.05
    echo -e "${CYAN} |  __ \ |  __ \(_) |  \/  |      | |        (_)           "
    sleep 0.05
    echo -e "${CYAN} | |__) || |__) |_  | \  / |  ___ | |_  _ __  _   ___  ___ "
    sleep 0.05
    echo -e "${CYAN} |  _  / |  ___/| | | |\/| | / _ \| __|| '__|| | / __|/ __|"
    sleep 0.05
    echo -e "${CYAN} | | \ \ | |    | | | |  | ||  __/| |_ | |   | || (__ \__ \\"
    sleep 0.05
    echo -e "${CYAN} |_|  \_\|_|    |_| |_|  |_| \___| \__||_|   |_| \___||___/"
    echo ""
    sleep 1
    echo -e "${NC}Make sure that you have downloaded this script from a trustworthy source!!"
    echo ""

    # Check for root privileges
    check_root

    # Stop and disable the service
    if sudo systemctl stop rpi-metricsd && sudo systemctl disable rpi-metricsd; then
        log_success "rpi-metricsd service stopped and disabled."
    else
        log_failure "Failed to stop or disable rpi-metricsd service. SKIPPING..."
    fi

    # Remove the systemd service file
    if sudo rm /etc/systemd/system/rpi-metricsd.service; then
        sudo systemctl daemon-reload
        log_success "Systemd service file removed and daemon reloaded."
    else
        log_failure "Failed to remove systemd service file. SKIPPING"
    fi

    # Remove the directory
    if sudo rm -rf /usr/share/rpi-metrics; then
        log_success "Directory /usr/share/rpi-metrics removed."
    else
        log_failure "Failed to remove /usr/share/rpi-metrics directory. SKIPPING"
    fi

    # Remove the custom alias rpi-metrics-update
    ALIAS_COMMAND="alias rpi-metrics-update='cd /usr/share/rpi-metrics && sudo git pull && sudo systemctl restart rpi-metricsd.service && cd -'"
    if grep -qxF "$ALIAS_COMMAND" /etc/bash.bashrc; then
        sudo sed -i "\|$ALIAS_COMMAND|d" /etc/bash.bashrc
        log_success "Alias rpi-metrics-update removed!" 
    else 
        log_failure "Failed to remove. Alias rpi-metrics-update does not exist! SKIPPING"
    fi

    # Remove the custom alias rpi-metrics-uninstall
    ALIAS_COMMAND="alias rpi-metrics-uninstall='sudo bash /usr/share/rpi-metrics/Server/uninstaller.sh'"
    if grep -qxF "$ALIAS_COMMAND" /etc/bash.bashrc; then
        sudo sed -i "\|$ALIAS_COMMAND|d" /etc/bash.bashrc
        log_success "Alias rpi-metrics-uninstall removed!" 
    else 
        log_failure "Failed to remove. Alias rpi-metrics-uninstall does not exist! SKIPPING"
    fi

    # Optionally remove python3 and related packages if --wet is used
    if [ "$REMOVE_PYTHON_PACKAGES" = true ]; then
        if sudo apt remove --purge -y python3 python3-pip python3-venv; then
            log_success "python3 and related packages removed."
        else
            log_failure "Failed to remove python3 and related packages."
        fi
    else
        echo "Skipping removal of python3 and related packages."
    fi

    echo "RPi Metrics uninstallation completed!"
}

# Check for --dry or --wet argument
if [ "$1" = "--extra-wet" ]; then
    REMOVE_PYTHON_PACKAGES=true
elif [ "$1" = "--wet" ]; then
    REMOVE_PYTHON_PACKAGES=false
else
    echo "Usage: $0 --wet | --extra-wet"
    echo "--wet: Standard uninstallation without removing Python packages."
    echo "--extra-wet: WARNING: USE WITH CARE!! Full uninstallation including removal of Python and Python packages."
    echo "YOU HAVE BEEN WARNED: DO NOT USE THE --extra-wet FLAG UNLESS YOU WANT TO REMOVE PYTHON FROM YOUR SYSTEM!!"
    exit 1
fi

# Call the main function
main "$@"
