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
if [[ "$ARCH" == "armv6l" ]]; then
    echo "Warning: You are running on ARMv6 (Pi Zero/1)."
    echo "Compiling Spotifyd on this device will take HOURS."
    echo "Press Ctrl+C to cancel, or wait 10 seconds to continue..."
    sleep 10
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
    "bt-agent"
    "bluez-tools"
    "curl"
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
if ! dpkg -l | grep -q carla-git; then
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
if ! command -v spotifyd &> /dev/null; then
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

# --- DEPLOY CONFIGS ---
echo -e "${YELLOW}--> Deploying Configs...${NC}"

# Spotifyd & PipeWire
mkdir -p "$USER_HOME/.config/spotifyd"
cp "$ASSETS_DIR/install/configs/spotifyd.conf" "$USER_HOME/.config/spotifyd/spotifyd.conf"
mkdir -p "$USER_HOME/.config/pipewire/pipewire.conf.d"
cp "$ASSETS_DIR/install/configs/virtual-cable.conf" "$USER_HOME/.config/pipewire/pipewire.conf.d/virtual-cable.conf"
# Fix permissions since we are running as sudo
chown -R $SUDO_USER:$SUDO_USER "$USER_HOME/.config"

# Carla Init & Merge
echo "Initializing Carla..."
# Run carla as user, timeout after 5s
sudo -u $SUDO_USER timeout 5s carla &
CARLA_PID=$!
sleep 5
kill -9 $CARLA_PID 2>/dev/null

echo "Merging Carla Settings..."
python3 "$ASSETS_DIR/install/scripts/configure_carla.py" "$USER_HOME/.config/falkTX/Carla2.conf"
check_status "Carla Config Merge"

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
After=network.target sound.target pipewire.service
Wants=pipewire.service

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/launch.sh
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
chown -R $SUDO_USER:$SUDO_USER "$(dirname "$SERVICE_FILE")"

# Enable service as the user
sudo -u $SUDO_USER systemctl --user enable nexo-speaker.service
loginctl enable-linger $SUDO_USER

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}   INSTALLATION COMPLETE! REBOOTING...   ${NC}"
echo -e "${GREEN}=========================================${NC}"
sleep 3
reboot now
exit 0