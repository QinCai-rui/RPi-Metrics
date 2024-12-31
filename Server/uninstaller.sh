#!/bin/bash
# Uninstallation script for RPi Metrics
# Created with love by QinCai with assistance from Copilot

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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
    echo "Starting RPi Metrics uninstallation..."

    # Check for root privileges
    check_root

    # Stop and disable the service
    if sudo systemctl stop rpi-metricsd && sudo systemctl disable rpi-metricsd; then
        log_success "rpi-metricsd service stopped and disabled."
    else
        log_failure "Failed to stop or disable rpi-metricsd service."
        exit 1
    fi

    # Remove the systemd service file
    if sudo rm /etc/systemd/system/rpi-metricsd.service; then
        sudo systemctl daemon-reload
        log_success "Systemd service file removed and daemon reloaded."
    else
        log_failure "Failed to remove systemd service file."
        exit 1
    fi

    # Remove the directory
    if sudo rm -rf /usr/share/rpi-metrics; then
        log_success "Directory /usr/share/rpi-metrics removed."
    else
        log_failure "Failed to remove /usr/share/rpi-metrics directory."
        exit 1
    fi

    # Optionally remove python3 and related packages
    confirm_remove_python() {
        read -r -p "Do you want to remove python3 and related packages? [y/n]: " yn
        case $yn in
            [Yy]* )
                if sudo apt remove --purge -y python3 python3-pip python3-venv; then
                    log_success "python3 and related packages removed."
                else
                    log_failure "Failed to remove python3 and related packages."
                fi
                ;;
            [Nn]* ) echo "Skipping removal of python3 and related packages." ;;
            * ) echo "Please answer yes or no."; confirm_remove_python ;;
        esac
    }

    confirm_remove_python

    echo "RPi Metrics uninstallation completed!"
}

# Call the main function
main "$@"
