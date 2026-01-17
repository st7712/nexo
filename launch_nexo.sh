#!/bin/bash

# Get the directory where this script is currently located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/src"

# Path to the virtual environment python executable
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

# 1. Force Display
export DISPLAY=:0

# 2. Mute AMP + DAC output
echo "Muting Amp..."
$VENV_PYTHON "$PROJECT_ROOT/mute.py"

# 3. Launch Carla
echo "Starting Carla..."
# It's usually better to check if it's already running to avoid duplicates
if ! pgrep -x "CarlaUE4-Linux-" > /dev/null; then
    /usr/bin/carla "./src/assets/DSP.carxp" &
fi

# 4. Launch Main Python Code
echo "Starting Main Controller..."
$VENV_PYTHON "$PROJECT_ROOT/main.py"