#!/bin/bash

echo "Running Pre-flight checks..."

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root. Please use sudo."
    echo "Try: sudo ./install.sh"
    exit 1
fi

if ! command -v apt-get >/dev/null; then
    echo "Error: Unsupported OS. This installer requires a Debian-based system (like Raspberry Pi OS)."
    exit 1
fi

# Check Architecture
# Spotifyd via Cargo is painful on single-core Pi Zero/1 (ARMv6).
ARCH=$(uname -m)
if [ "$ARCH" != "armv7l" ] && [ "$ARCH" != "aarch64" ] && [ "$ARCH" != "x86_64" ]; then
    echo "Error: Unsupported architecture: $ARCH"
    echo "Supported architectures are: armv7l (ARMv7), aarch64 (ARMv8), x86_64."
    exit 1
fi

# --- CONFIGURATION ---
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ASSETS_DIR="$PROJECT_DIR/assets"
USER_HOME="/home/$SUDO_USER" # Get the real user, not root
VENV_DIR="$PROJECT_DIR/.venv"

# If sudo wasn't used correctly, fallback to current user
if [ -z "$SUDO_USER" ]; then
    USER_HOME="/home/$USER"
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK] $1${NC}"
    else
        echo -e "${RED}[ERROR] $1 failed!${NC}"
        echo -e "${RED}Try re-running the installer.${NC}"
        exit 1
    fi
}

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}      NEXO HOME SPEAKER INSTALLER        ${NC}"
echo -e "${GREEN}      Architecture: $ARCH                ${NC}"
echo -e "${GREEN}=========================================${NC}"

# --- DEPENDENCY CHECK LOOP ---
REQUIRED_PKGS=(
    "git"
    "build-essential"
    "python3-dev"
    "python3-venv"
    "libasound2-dev"
    "libssl-dev"
    "pkg-config"
    "gpgv"
    "wget"
    "pamixer"
    "liblgpio-dev"
    "swig"
    "bluez-tools"
    "curl"
    "p7zip-full"
    "playerctl"
    "pulseaudio-utils"
    "xvfb"
    "libdbus-1-dev"
)

echo -e "${YELLOW}--> Checking System Dependencies...${NC}"
sudo apt-get update

PKGS_TO_INSTALL=""
for pkg in "${REQUIRED_PKGS[@]}"; do
    # Check if package is installed
    if ! dpkg -l | grep -q "^ii  $pkg "; then
        echo "Missing package: $pkg"
        PKGS_TO_INSTALL="$PKGS_TO_INSTALL $pkg"
    fi
done

if [ ! -z "$PKGS_TO_INSTALL" ]; then
    echo "Installing missing packages: $PKGS_TO_INSTALL"
    sudo apt-get install -y $PKGS_TO_INSTALL
    check_status "Dependency Installation"
else
    echo -e "${GREEN}[OK] All system dependencies are already installed.${NC}"
fi

# --- SET HOSTNAME ---
echo -e "${YELLOW}--> Setting Hostname...${NC}"
hostnamectl set-hostname "Nexo Home" --pretty
check_status "Hostname set"

# --- PYTHON VENV SETUP ---
echo -e "${YELLOW}--> Setting up Python VENV...${NC}"
if [ ! -d "$VENV_DIR" ]; then
    # Create venv as the REAL user, not root
    sudo -u $SUDO_USER python3 -m venv "$VENV_DIR"
    check_status "Venv Created"
fi

echo "Installing Python Requirements..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    pip install -r "$PROJECT_DIR/requirements.txt"
    check_status "Pip Requirements"
fi
deactivate

# --- INSTALL CARLA ---
echo -e "${YELLOW}--> Checking Carla...${NC}"
if ! dpkg -l | grep -q carla; then
    wget https://launchpad.net/~kxstudio-debian/+archive/kxstudio/+files/kxstudio-repos_11.2.0_all.deb
    dpkg -i kxstudio-repos_11.2.0_all.deb
    apt-get update
    apt-get install -y carla
    rm kxstudio-repos_11.2.0_all.deb
    check_status "Carla Installation"
else
    echo -e "${GREEN}[OK] Carla is already installed.${NC}"
fi

# --- INSTALL SPOTIFYD ---
echo -e "${YELLOW}--> Checking Spotifyd...${NC}"
if ! sudo -u "$SUDO_USER" command -v spotifyd &> /dev/null; then
    echo "Spotifyd not found. Installing Rust/Cargo..."
    
    # Install Rust as the user (not root)
    if ! sudo -u $SUDO_USER command -v cargo &> /dev/null; then
        sudo -u $SUDO_USER curl https://sh.rustup.rs -sSf | sudo -u $SUDO_USER sh -s -- -y
    fi

    # Add cargo to path for this session
    source "$USER_HOME/.cargo/env"

    echo "Compiling Spotifyd (This will take time)..."
    # Run cargo install as the user
    sudo -u $SUDO_USER "$USER_HOME/.cargo/bin/cargo" install spotifyd --features "dbus_mpris,pulseaudio_backend" --locked

    # Symlink binary for system-wide access
    ln -sf "$USER_HOME/.cargo/bin/spotifyd" /usr/bin/spotifyd
    check_status "Spotifyd Compilation"
else
    echo -e "${GREEN}[OK] Spotifyd is already installed.${NC}"
fi

if ! command -v spotifyd &> /dev/null; then
    echo -e "${RED}Error: spotifyd installation failed.${NC}"
    exit 1
fi

# --- DEPLOY CONFIGS ---
echo -e "${YELLOW}--> Deploying Configs...${NC}"

# Spotifyd & PipeWire
mkdir -p "$USER_HOME/.config/spotifyd"
cp "$ASSETS_DIR/install/configs/spotifyd.conf" "$USER_HOME/.config/spotifyd/spotifyd.conf"
mkdir -p "$USER_HOME/.config/pipewire/pipewire.conf.d"
cp "$ASSETS_DIR/install/configs/virtual-cable.conf" "$USER_HOME/.config/pipewire/pipewire.conf.d/virtual-cable.conf"
mkdir -p "$USER_HOME/.config/falkTX"
cp "$ASSETS_DIR/install/configs/Carla2.conf" "$USER_HOME/.config/falkTX/Carla2.conf"
# Fix permissions since we are running as sudo
chown -R $SUDO_USER:$SUDO_USER "$USER_HOME/.config"

# --- INSTALL LSP PLUGINS ---
echo -e "${YELLOW}--> Installing LSP Plugins (VST)...${NC}"

# Get correct Download URL
LSP_VERSION="1.2.26"
BASE_URL="https://github.com/sadko4u/lsp-plugins/releases/download/$LSP_VERSION"

if [[ "$ARCH" == "x86_64" ]]; then
    LSP_FILE="lsp-plugins-$LSP_VERSION-Linux-x86_64.7z"
elif [[ "$ARCH" == "aarch64" ]]; then
    LSP_FILE="lsp-plugins-$LSP_VERSION-Linux-aarch64.7z"
elif [[ "$ARCH" == "armv7l" ]]; then
    LSP_FILE="lsp-plugins-$LSP_VERSION-Linux-arm32.7z"
else
    echo -e "${RED}Error: Unsupported architecture $ARCH for LSP Plugins.${NC}"
    exit 1
fi

# Check if already installed
if [ -d "/usr/lib/vst/lsp-plugins.vst" ]; then
    echo -e "${GREEN}[OK] LSP Plugins already installed.${NC}"
else
    echo "Downloading $LSP_FILE..."

    # Download
    wget "$BASE_URL/$LSP_FILE" -O "$LSP_FILE"
    
    # Extract to a temp folder
    echo "Extracting..."
    mkdir -p lsp_temp
    7z x "$LSP_FILE" -olsp_temp > /dev/null

    # Move the VST2 folder to the correct system location
    echo "Installing to /usr/lib/vst..."
    sudo mkdir -p /usr/lib/vst

    # Find the VST2 folder regardless of internal naming
    VST_SOURCE=$(find lsp_temp -type d -name "lsp-plugins.vst" | head -n 1)
    
    if [ -d "$VST_SOURCE" ]; then
        sudo cp -r "$VST_SOURCE" /usr/lib/vst/
        check_status "LSP VST Installation"
    else
        echo -e "${RED}Error: Could not find lsp-plugins.vst inside archive!${NC}"
        exit 1
    fi

    # Cleanup
    rm "$LSP_FILE"
    rm -rf lsp_temp
fi

# PulseAudio
PA_CONF="/etc/pulse/daemon.conf"
if [ ! -f "$PA_CONF.bak" ]; then cp "$PA_CONF" "$PA_CONF.bak"; fi

if grep -q "NEXO AUDIO OPTIMIZATIONS" "$PA_CONF"; then
    echo "PulseAudio already optimized."
else
    cat >> $PA_CONF <<EOF

# --- NEXO AUDIO OPTIMIZATIONS ---
daemonize = yes
high-priority = yes
nice-level = -11
realtime-scheduling = yes
realtime-priority = 9
resample-method = speex-float-10
avoid-resampling = yes
default-sample-rate = 48000
alternate-sample-rate = 48000
default-fragments = 8
default-fragment-size-msec = 10
# --------------------------------
EOF
fi

echo "Configuring PipeWire"
    # Create a drop-in config for PipeWire to force 48kHz
    PW_CONF_DIR="$USER_HOME/.config/pipewire/pipewire.conf.d"
    mkdir -p "$PW_CONF_DIR"

    cat <<EOF > "$PW_CONF_DIR/10-nexo-rate.conf"
context.properties = {
    default.clock.rate = 48000
    default.clock.allowed-rates = [ 48000 ]
    default.clock.quantum = 1024
}
EOF
    chown -R $SUDO_USER:$SUDO_USER "$USER_HOME/.config/pipewire"
    check_status "PipeWire Optimization"

# --- BLUETOOTH CONFIG ---
echo -e "${YELLOW}--> Configuring Bluetooth...${NC}"
BT_CONF="/etc/bluetooth/main.conf"
if [ ! -f "$BT_CONF.bak" ]; then cp "$BT_CONF" "$BT_CONF.bak"; fi

sed -i 's/^#\?Name = .*/Name = Nexo Home/' "$BT_CONF"
sed -i 's/^#\?Class = .*/Class = 0x240414/' "$BT_CONF"
sed -i 's/^#\?DiscoverableTimeout = .*/DiscoverableTimeout = 180/' "$BT_CONF"

if grep -q "JustWorksRepairing" "$BT_CONF"; then
    sed -i 's/^#\?JustWorksRepairing = .*/JustWorksRepairing = always/' "$BT_CONF"
else
    sed -i '/^\[General\]/a JustWorksRepairing = always' "$BT_CONF"
fi

# --- SERVICES & AUTOSTART ---
echo -e "${YELLOW}--> Setting up Services...${NC}"

# BT Agent
cp "$ASSETS_DIR/install/services/bt-agent.service" /etc/systemd/system/bt-agent.service
systemctl daemon-reload
systemctl enable bt-agent
systemctl start bt-agent

# User Service for Main Script
SERVICE_FILE="$USER_HOME/.config/systemd/user/nexo-speaker.service"
mkdir -p "$(dirname "$SERVICE_FILE")"
cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Nexo Smart Speaker Controller
After=network.target sound.target pipewire.service graphical-session.target bluetooth.service
Wants=pipewire.service bluetooth.service

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStartPre=/bin/sleep 30
ExecStart=$PROJECT_DIR/launch.sh
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
chown -R $SUDO_USER:$SUDO_USER "$(dirname "$SERVICE_FILE")"

# Enable service as the user
# Enable "Lingering" first (Crucial for headless operation)
loginctl enable-linger $SUDO_USER

# Get the User ID (usually 1000 for the first user)
TARGET_UID=$(id -u $SUDO_USER)
export XDG_RUNTIME_DIR="/run/user/$TARGET_UID"

# Enable the service explicitly setting the Bus location
echo "Enabling service for user: $SUDO_USER (UID: $TARGET_UID)..."
sudo -E -u $SUDO_USER systemctl --user daemon-reload
sudo -E -u $SUDO_USER systemctl --user enable nexo-speaker.service
check_status "Service Enable"

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}   INSTALLATION COMPLETE! REBOOTING...   ${NC}"
echo -e "${GREEN}=========================================${NC}"
sleep 3
reboot now
exit 0
