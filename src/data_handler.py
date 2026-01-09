import json
import os
import uuid
import system_helper as system

CONFIG_FILE = "/home/pi/nexo/src/nexo_config.json"
DEFAULT_CONFIG = {
    "device_name": "Nexo Home",
    "device_id": uuid.uuid4().hex,
    "volume": 100,
    "sounds": True,
    "wifi": {
        "ssid": system.get_current_wifi_ssid() or "",
        "password": ""
    },
    "eq_presets": {
        "bass": {
            0: {"16": 0.5, "25": 0.5, "40": 0.5, "63": 0.5, "100": 0.5, "160": 0.5, "250": 0.5},
            1: {"16": 0.51, "25": 0.51, "40": 0.51, "63": 0.51, "100": 0.51, "160": 0.51, "250": 0.51},
            2: {"16": 0.53, "25": 0.53, "40": 0.53, "63": 0.53, "100": 0.53, "160": 0.53, "250": 0.53},
            3: {"16": 0.54, "25": 0.54, "40": 0.54, "63": 0.54, "100": 0.54, "160": 0.54, "250": 0.54},
            4: {"16": 0.56, "25": 0.56, "40": 0.56, "63": 0.56, "100": 0.56, "160": 0.56, "250": 0.56},
            5: {"16": 0.57, "25": 0.57, "40": 0.57, "63": 0.57, "100": 0.57, "160": 0.57, "250": 0.57},
            6: {"16": 0.59, "25": 0.59, "40": 0.59, "63": 0.59, "100": 0.59, "160": 0.59, "250": 0.59}
        },
        "treble": {
            0: {"1600": 0.5, "2500": 0.5, "4000": 0.5, "6300": 0.5, "10000": 0.5, "16000": 0.5},
            1: {"1600": 0.51, "2500": 0.51, "4000": 0.51, "6300": 0.51, "10000": 0.51, "16000": 0.51},
            2: {"1600": 0.53, "2500": 0.53, "4000": 0.53, "6300": 0.53, "10000": 0.53, "16000": 0.53},
            3: {"1600": 0.54, "2500": 0.54, "4000": 0.54, "6300": 0.54, "10000": 0.54, "16000": 0.54},
            4: {"1600": 0.56, "2500": 0.56, "4000": 0.56, "6300": 0.56, "10000": 0.56, "16000": 0.56},
            5: {"1600": 0.57, "2500": 0.57, "4000": 0.57, "6300": 0.57, "10000": 0.57, "16000": 0.57},
            6: {"1600": 0.59, "2500": 0.59, "4000": 0.59, "6300": 0.59, "10000": 0.59, "16000": 0.59}
        },
        "flat": {}
    },
    "current_eq_bass": 0,
    "current_eq_treble": 0,
    "master": True
}

class DataHandler:
    def __init__(self, filepath=CONFIG_FILE):
        self.filepath = filepath
        self.data = self._load_data()

    def _load_data(self):
        """Loads JSON from disk or creates default if missing."""
        if not os.path.exists(self.filepath):
            print(f"Config file not found. Creating default at {self.filepath}")
            self._save_to_disk(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}. Reverting to default.")
            return DEFAULT_CONFIG.copy()

    def _save_to_disk(self, data):
        """Atomic write: Write to temp, then rename."""
        temp_file = f"{self.filepath}.tmp"
        try:
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=4)
            
            # Atomic move
            os.replace(temp_file, self.filepath)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def get(self, key, default=None):
        """Get a specific setting."""
        return self.data.get(key, default)

    def set(self, key, value):
        """Update a specific setting and save to disk."""
        self.data[key] = value
        self._save_to_disk(self.data)
        return self.data[key]

    def get_all(self):
        return self.data
    
    def reset_to_default(self):
        """Resets the config file to default settings."""
        self.data = DEFAULT_CONFIG.copy()
        self._save_to_disk(self.data)

# Create a singleton instance to be shared across modules
db = DataHandler()