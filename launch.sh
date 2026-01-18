#!/bin/bash

# Get the directory where this script is currently located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/src"

# Path to the virtual environment python executable
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

# Wait for PipeWire to be ready
sleep 15

# Mute AMP + DAC output
echo "Muting Amp..."
$VENV_PYTHON "$PROJECT_ROOT/mute.py"

# Launch Carla
echo "Starting Carla..."
# It's usually better to check if it's already running to avoid duplicates
if ! pgrep -x "carla" > /dev/null; then
    xvfb-run -a /usr/bin/carla "$SCRIPT_DIR/assets/config/DSP.carxp" &
    # Wait for Carla to load
    echo "Waiting for Carla process..."
    for i in {1..15}; do
        if pgrep -f "carla" > /dev/null; then
            echo "Carla started!"
            break
        fi
        sleep 1
    done

    sleep 5
fi

# Launch Main Python Code
echo "Starting Main Controller..."
$VENV_PYTHON "$PROJECT_ROOT/main.py"