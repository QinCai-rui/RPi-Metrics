#!/usr/bin/env bash
# This script took inspiration from the Pi-Hole and RaspAP installer script.
# Created with love by QinCai with assistance from Copilot (The colour parts)
# ASCII art generated by https://patorjk.com/software/taag/
# MAKE SURE THAT YOU HAVE DOWNLOADED THIS SCRIPT FROM A TRUST-WORTHY SOURCE!!!

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

generate_api_key() {
    local length=32
    local api_key
    
    # Try using OpenSSL first
    if command -v openssl &> /dev/null; then
        api_key=$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c ${length})
    else
        # Fallback to /dev/urandom
        api_key=$(head -c 32 /dev/urandom | tr -dc 'A-Za-z0-9' | head -c ${length})
    fi
    
    if [[ ${#api_key} -eq ${length} ]]; then
        echo "${api_key}"
        return 0
    else
        log_failure "Failed to generate API key"
        return 1
    fi
}

mandatory_confirm() {
    if [ "$AUTO_CONFIRM" = true ]; then
        return 0
    fi

    read -r -p "$1 [y/n]: " yn
    case $yn in
        [Yy]* ) return 0;;
        [Nn]* ) echo -e "${RED}Installation aborted.${NC}"; exit 1;;
        * ) echo -e "${YELLOW}Please answer yes or no. Defaulting to yes${NC}";;
    esac
}

acknowledge() {
    if [ "$AUTO_CONFIRM" = true ]; then
        return 0
    fi

    echo ""
    read -r -p "Hit enter to acknowledge" -n1
    # Move cursor up one line, clear the line
    tput cuu1 && tput el
}

if [ "$1" = "-y" ]; then
    AUTO_CONFIRM=true
fi

if [ "$1" = "--no-check-root" ]; then 
    NO_CHECK_ROOT=true 
fi

log_success() {
    echo -e "${GREEN}[\u2714] $1${NC}"
}

log_failure() {
    echo -e "${RED}[\u2718] $1${NC}"
}

log_info() {
    echo -e "${BLUE}[\u2139] $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[\u26a0] $1${NC}"
}

check_network() {
    log_info "Checking network connectivity..."
    sleep 0.25
    
    # Try to reach GitHub (needed for git clone)
    if ! ping -c 1 github.com &> /dev/null; then
        log_failure "Cannot reach github.com. Check your internet connection."
        return 1
    fi
    
    log_success "Network connectivity confirmed"
    return 0
}

check_system_requirements() {
    log_info "Checking system requirements..."
    sleep 0.25
    
    # Check available disk space
    local required_space=256000  # 250MiB in KiB
    local available_space
    available_space=$(df -k /usr/share | awk 'NR==2 {print $4}')
    
    if [ "${available_space}" -lt "${required_space}" ]; then
        log_failure "Insufficient disk space. Need at least 250MiB free."
        return 1
    fi
    
    # Check RAM
    local required_ram=1048576  # 1GiB in KiB
    local available_ram
    available_ram=$(free -k | awk '/^Mem:/ {print $2}')
    
    if [ "${available_ram}" -lt "${required_ram}" ]; then
        log_warning "Insufficient RAM. Need at least 1GiB."
        log_warning "Performance may be impacted."
        return 0
    fi
    
    log_success "System requirements met"
    return 0
}

check_root() { 
    log_info "Checking for root privileges..." 
    sleep 0.25
    if [ "$NO_CHECK_ROOT" = true ]; then 
        log_warning "Skipping root check due to --no-check-root flag." 
        return 0 
    fi 
    
    if [ "$EUID" -ne 0 ]; then 
        log_failure "Please run as root." 
        echo "If you encountered any problems, please check out https://github.com/QinCai-rui/RPi-Metrics/blob/main/README.md!"
        exit 1 
    else 
        log_success "Running as root." 
    fi 
}

check_rpi() {
    log_info "Checking if running on a Raspberry Pi..."
    sleep 0.25
    if grep -q "Raspberry Pi" /proc/cpuinfo; then
        log_success "Running on a Raspberry Pi."
    else
        log_failure "This script can only be run on a Raspberry Pi."
        echo "If you encountered any problems, please check out https://github.com/QinCai-rui/RPi-Metrics/blob/main/README.md!"
        exit 1
    fi
}

check_curl() {
    log_info "Checking for curl..."
    sleep 0.25
    if ! command -v curl &> /dev/null; then
        log_failure "curl could not be found."
        mandatory_confirm "Install curl?"
        sudo apt-get update && sudo apt-get install -y curl
        log_success "curl installed!"
    else
        log_success "curl is already installed."
    fi
}

check_git() {
    log_info "Checking for git..."
    sleep 0.25
    if ! command -v git &> /dev/null; then
        log_failure "git could not be found."
        mandatory_confirm "Install git?"
        sudo apt-get update && sudo apt-get install -y git
        log_success "git installed!"
    else
        log_success "git is already installed."
    fi
}

check_git() {
    log_info "Checking for jq..."
    sleep 0.25
    if ! command -v jq &> /dev/null; then
        log_failure "jq could not be found."
        mandatory_confirm "Install jq?"
        sudo apt-get update && sudo apt-get install -y jq
        log_success "jq installed!"
    else
        log_success "jq is already installed."
    fi
}

check_vcgencmd() {
    log_info "Checking installation of vcgencmd..."
    sleep 0.25
    if ! command -v vcgencmd &> /dev/null; then
        log_failure "vcgencmd could not be found."
        mandatory_confirm "Install vcgencmd and other packages?"

        log_info "Installing compilers..."
        sudo apt-get install -y cmake gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
        log_success "Compilers installed."

        log_info "Downloading Userland..."
        cd /tmp
        git clone https://github.com/raspberrypi/userland.git
        cd userland
        log_success "Downloaded Userland."

        log_info "Building from source... This might take a while."
        ./buildme --aarch64
        log_success "Build complete!"

        log_info "Performing some housekeeping..."
        sudo mv build/bin/vcgencmd /usr/local/bin/vcgencmd
        sudo chown root:video /usr/local/bin/vcgencmd
        sudo chmod 775 /usr/local/bin/vcgencmd
        sudo mv build/lib/libvchiq_arm.so build/lib/libvcos.so /lib/
        log_success "Housekeeping done."

        log_info "Adding user to the video group..."
        sudo usermod -aG video root
        log_success "User added to the video group."

        log_info "Setting up udev rules..."
        echo 'SUBSYSTEM=="vchiq", GROUP="video", MODE="0660"' | sudo tee /etc/udev/rules.d/99-input.rules
        sudo udevadm control --reload-rules && sudo udevadm trigger
        log_success "Udev rules set up."
        if ! command -v vcgencmd &> /dev/null; then
            log_failure "FATAL: vcgencmd not found!!!"
        else
            sudo rm -rf /tmp/userland/
            log_success "vcgencmd installed!"
        fi
    else
        log_success "vcgencmd is already installed."
    fi
}

get_latest_release() {
    if release_tag=$(curl -s -H "Accept: application/vnd.github+json" https://api.github.com/repos/QinCai-rui/RPi-Metrics/releases/latest | jq -r .tag_name); then
        echo "Version: $release_tag"
        echo ""
    else
        echo "N/A"
        log_failure "Failed to get the latest release."
        echo ""
    fi
}

main() {
    clear
    echo "Welcome to the RPi Metrics installation script!"
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
    get_latest_release
    sleep 1
    echo -e "${NC}Make sure that you have downloaded this script from a trustworthy source!!"
    echo ""
    sleep 1.5

    check_root
    echo
    sleep 0.75

    check_network || exit 1
    echo
    sleep 0.75

    check_system_requirements || exit 1
    echo
    sleep 0.75

    check_rpi
    echo
    sleep 0.75

    check_git
    echo
    sleep 0.75

    check_curl
    echo

    mandatory_confirm "Update your package list and install necessary packages?"

    log_info "Updating package list and installing necessary packages..."
    # Update package list and install necessary packages
    if sudo apt-get update && sudo apt-get upgrade -y && sudo apt-get install -y python3 python3-pip python3-venv; then
        log_success "Package list updated and necessary packages installed."
    else
        log_failure "Failed to update package list or install necessary packages."
        echo "If you encountered any problems, please check out https://github.com/QinCai-rui/RPi-Metrics/blob/main/README.md!"
        exit 1
    fi

    check_vcgencmd

    mandatory_confirm "Create a directory for rpi-metrics in /usr/share?"

    log_info "Creating directory for rpi-metrics..."
    # Create a directory for rpi-metrics
    if sudo mkdir -p /usr/share/rpi-metrics && cd /usr/share/rpi-metrics; then
        log_success "Directory for rpi-metrics created in /usr/share."
    else
        log_failure "Failed to create directory for rpi-metrics."
        echo "If you encountered any problems, please check out https://github.com/QinCai-rui/RPi-Metrics/blob/main/README.md!"
        exit 1
    fi

    mandatory_confirm "Clone the RPi-Metrics repository?"

    log_info "Cloning the RPi-Metrics repository..."
    # Clone the repository
    if sudo git -c http.followRedirects=true clone https://github.com/QinCai-rui/RPi-Metrics.git /usr/share/rpi-metrics; then
        log_success "RPi-Metrics server repository cloned successfully."
    else
        log_failure "Failed to clone RPi-Metrics server repository."
        log_warning "If you have an older version of this program, make sure you have removed it before re-installing it!"
        log_info "Run this to uninstall, if installed:"
        echo -e "${MAGENTA}   curl -sL https://qincai.xyz/rpi-metrics-uninstaller.sh | sudo bash -s - --wet${NC}"
        exit 1
    fi

    log_info "Setting up the Flask application environment..."

    # Navigate to the server directory
    cd /usr/share/rpi-metrics/Server

    # Create a virtual environment for the Flask app
    log_info "Creating a Python virtual environment..."
    sudo python3 -m venv venv
    log_success "Python virtual environment created."

    # Activate the virtual environment
    source venv/bin/activate

    # Install necessary Python packages
    log_info "Installing required Python packages..."
    sudo venv/bin/pip install Flask
    sudo venv/bin/pip install Flask-Limiter
    log_success "Python packages installed."

    # Generate an API key
    API_KEY=$(generate_api_key)
    log_success "Generated API key: $API_KEY"

    # Create an env.py file with the necessary configuration
    log_info "Creating env.py configuration file..."
    sudo tee /usr/share/rpi-metrics/Server/env.py > /dev/null <<EOL
API_KEY = "$API_KEY"
EOL
    log_success "env.py configuration file created."

    # Set permissions for the Flask application directory
    log_info "Setting permissions for the Flask application directory..."
    sudo chown -R $USER:$USER /usr/share/rpi-metrics/Server
    log_success "Permissions set."

    log_info "Copying the systemd service file..."
    # Copy the systemd service file
    if sudo cp /usr/share/rpi-metrics/Server/rpi-metricsd.service /etc/systemd/system/; then
        log_success "Systemd service file copied successfully."
    else
        log_failure "Failed to copy systemd service file."
        echo "If you encountered any problems, please check out https://github.com/QinCai-rui/RPi-Metrics/blob/main/README.md!"
        exit 1
    fi

    log_info "Adding custom alias rpi-metrics-update..."
    # Define the alias command 
    ALIAS_COMMAND="alias rpi-metrics-update='cd /usr/share/rpi-metrics && sudo git pull && sudo systemctl restart rpi-metricsd.service && cd - > /dev/null'"
    # Check if the alias is already in the file 
    if grep -qxF "$ALIAS_COMMAND" /etc/bash.bashrc; then
        log_warning "Alias already exists!"
    else
        echo "$ALIAS_COMMAND" | sudo tee -a /etc/bash.bashrc > /dev/null
        log_success "Alias rpi-metrics-update added!"
    fi

    log_info "Adding custom alias rpi-metrics-uninstall..."
    # Define the alias command 
    ALIAS_COMMAND="alias rpi-metrics-uninstall='sudo bash /usr/share/rpi-metrics/Server/uninstaller.sh'"
    if grep -qxF "$ALIAS_COMMAND" /etc/bash.bashrc; then
        log_warning "Alias already exists!"
    else
        echo "$ALIAS_COMMAND" | sudo tee -a /etc/bash.bashrc > /dev/null
        log_success "Alias rpi-metrics-uninstall added!"
    fi

    # Source the bashrc file
    log_info "Sourcing /etc/bash.bashrc..."
    if source /etc/bash.bashrc; then
        log_success "Sourced /etc/bash.bashrc"
    else
        log_failure "Failed to source /etc/bash.bashrc. Please do so manually"
    fi

    log_info "Reloading systemd daemon..."
    # Reload systemd daemon
    if sudo systemctl daemon-reload; then
        log_success "Systemd daemon reloaded."
    else
        log_failure "Failed to reload systemd daemon."
    fi

    mandatory_confirm "Start and enable the rpi-metricsd service?"

    log_info "Starting and enabling the rpi-metricsd service..."
    # Start and enable the rpi-metricsd service
    if sudo systemctl start rpi-metricsd && sudo systemctl enable rpi-metricsd; then
        log_success "rpi-metricsd service started and enabled."
    else
        log_failure "Failed to start or enable rpi-metricsd service."
        echo "If you encountered any problems, please check out https://github.com/QinCai-rui/RPi-Metrics/blob/main/README.md!"
        exit 1
    fi

    log_success "RPi Metrics Server installation completed!"

    # Inform the user about starting the Flask app
    log_info "The Flask server is set to automatically start on startup"
    echo -e "${BLUE}To disable it, run:${NC}"
    echo -e "${MAGENTA}   sudo systemctl disable rpi-metricsd${NC}"

    acknowledge

    log_warning "VERY VERY VERY IMPORTANT!!"
    echo -e "${BLUE}The generated API key has been added to the env.py file."
    echo -e "${BLUE}You can find and modify it in /usr/share/rpi-metrics/Server/env.py if needed.${NC}"
    echo
    echo -e "Generated API key: $API_KEY"

    acknowledge

    echo -e "${BLUE}Available API Endpoints:${NC}"
    echo -e "${MAGENTA}/api/time${NC}"
    echo -e "${CYAN}   - Method: GET${NC}"
    echo -e "${CYAN}   - Description: Retrieve the current system time.${NC}"

    acknowledge

    echo -e "${MAGENTA}/api/mem${NC}"
    echo -e "${CYAN}   - Method: GET${NC}"
    echo -e "${CYAN}   - Description: Retrieve memory statistics.${NC}"

    acknowledge

    echo -e "${MAGENTA}/api/cpu${NC}"
    echo -e "${CYAN}   - Method: GET${NC}"
    echo -e "${CYAN}   - Description: Retrieve CPU usage.${NC}"

    acknowledge

    echo -e "${MAGENTA}/api/shutdown${NC}"
    echo -e "${CYAN}   - Method: POST${NC}"
    echo -e "${CYAN}   - Description: Shutdown the system (requires API key in the header).${NC}"

    acknowledge

    echo -e "${MAGENTA}/api/update${NC}"
    echo -e "${CYAN}   - Method: POST${NC}"
    echo -e "${CYAN}   - Description: Update the system (requires API key in the header).${NC}"

    acknowledge

    echo -e "${MAGENTA}/api/all${NC}"
    echo -e "${CYAN}   - Method: GET${NC}"
    echo -e "${CYAN}   - Description: Retrieve comprehensive system statistics.${NC}"

    acknowledge

    echo "That's about it from me!"

    echo "HAVE FUN!!!"

    echo ""

    echo "If you encountered any problems, please check out https://github.com/QinCai-rui/RPi-Metrics/blob/main/README.md!"

    log_success "RPi Metrics installation completed!"
}

main "$@"
