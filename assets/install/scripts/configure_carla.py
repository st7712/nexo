import configparser
import os
import sys

# Get the path from arguments or default
if len(sys.argv) > 1:
    config_path = sys.argv[1]
else:
    # Fallback default
    config_path = os.path.expanduser("~/.config/falkTX/Carla2.conf")

print(f"Merging settings into: {config_path}")

config = configparser.ConfigParser()
config.optionxform = str  # Preserve case sensitivity

# Load existing if available
if os.path.exists(config_path):
    config.read(config_path)

# Ensure sections exist
if not config.has_section("Engine"):
    config.add_section("Engine")
if not config.has_section("OSC"):
    config.add_section("OSC")

# --- NEXO SETTINGS ---
settings_map = {
    "Engine": {
        "AudioDriver": "PulseAudio",
        r"Driver-PulseAudio\BufferSize": "1024",
        r"Driver-PulseAudio\Device": "",
        r"Driver-PulseAudio\SampleRate": "48000"
    },
    "OSC": {
        "Enabled": "true",
        "TCPEnabled": "true",
        "TCPNumber": "22752",
        "TCPRandom": "false",
        "UDPEnabled": "true",
        "UDPNumber": "22752",
        "UDPRandom": "false"
    }
}

# Apply settings
for section, options in settings_map.items():
    for key, value in options.items():
        config.set(section, key, value)

# Write back
try:
    with open(config_path, 'w') as f:
        config.write(f)
    print("SUCCESS: Carla configuration updated.")
except Exception as e:
    print(f"ERROR: Could not write config: {e}")
    sys.exit(1)