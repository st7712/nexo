from pythonosc import udp_client

# Config
IP = "127.0.0.1"
PORT = 22752  # Default Carla OSC port

client = udp_client.SimpleUDPClient(IP, PORT)

# Constants

# Plugin IDs
PLUGIN_EQ = 0
WOOFER_SPLITTER = 1
OTHER_SPLITTER = 2

# Parameter ID for "Master" volume on the Splitters
PARAM_SPLITTER_MASTER = 3 

# Mapping Frequency (Hz) -> Parameter Index for "LSP Graphic Equalizer"
EQ_BANDS = {
    16:   14,
    25:   18,
    40:   22,
    63:   26,
    100:  30,
    160:  34,
    250:  38,
    400:  42,
    630:  46,
    1000: 50,
    1600: 54,
    2500: 58,
    4000: 62,
    6300: 66,
    10000: 70,
    16000: 74
}

# Functions

def _send_carla_command(plugin_id, param_id, value):
    """
    Sends the OSC command: /Carla/<plugin_id>/set_parameter_value <param_id> <value>
    """
    address = f"/Carla/{plugin_id}/set_parameter_value"
    try:
        # Arguments: Parameter ID (int), Value (float)
        client.send_message(address, [int(param_id), float(value)])
    except Exception as e:
        print(f"OSC Error: {e}")

def set_eq_gain(freq, gain_val):
    """
    Sets the gain for a specific frequency band.
    freq: The frequency (e.g., 40, 63, 1000)
    gain_val: The gain (usually 0.0 to maybe 4.0 or -20.0 depending on plugin)
              According to XML default '1', standard is likely 1.0 = 0dB.
    """
    if freq not in EQ_BANDS:
        print(f"Error: Frequency {freq}Hz not found in EQ map.")
        return

    param_id = EQ_BANDS[freq]
    _send_carla_command(PLUGIN_EQ, param_id, gain_val)
    print(f"EQ: Set {freq}Hz to {gain_val}")

def set_splitter_volume(splitter_num, volume_db):
    """
    Sets the Master volume of the splitters.
    splitter_num: 1 or 2
    volume_db: The value (XML default shows -12 or 0)
    """
    if splitter_num == 1:
        plugin_id = WOOFER_SPLITTER
    elif splitter_num == 2:
        plugin_id = OTHER_SPLITTER
    else:
        print("Error: Invalid splitter number (use 1 or 2)")
        return

    _send_carla_command(plugin_id, PARAM_SPLITTER_MASTER, volume_db)
    print(f"Splitter {splitter_num}: Master set to {volume_db}")

# Reset EQ to flat
def reset_eq_flat():
    print("Resetting EQ to flat (1.0)...")
    for freq in EQ_BANDS:
        set_eq_gain(freq, 0.0)