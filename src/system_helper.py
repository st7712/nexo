import subprocess
import os
import time

def is_spotify_active():
    """
    Checks if a user is actively connected to Spotifyd.
    Returns True if Connected (Playing/Paused/Stopped but session active).
    Returns False if disconnected.
    """
    try:
        # We check if spotifyd appears in the player list
        # If no user is connected, spotifyd usually doesn't show up in playerctl -l
        output = subprocess.check_output(["playerctl", "-l"], text=True)
        status = subprocess.check_output(["playerctl", "status"], text=True).strip()
        if "spotifyd" in output:
            print("Spotifyd is active.")
            if status == "Playing":
                print("Spotifyd is currently playing.")
                return True, status
            elif status == "Paused":
                print("Spotifyd is currently paused.")
                return True, status
            elif status == "Stopped":
                print("Spotifyd is currently stopped.")
                return False, status
        else:
            print("No active Spotifyd session.")
            return False, status
        
        return "spotifyd" in output
    except subprocess.CalledProcessError:
        return False, None

def play_sound(filepath, volume=16384):
    """
    Plays a WAV file through PulseAudio/PipeWire using paplay.
    """
    if os.path.exists(filepath):
        subprocess.Popen(["paplay", filepath, f"--volume={volume}"])  # Volume is 0-65536
    else:
        print(f"Sound file not found: {filepath}")

def restart_spotifyd():
    """
    Kicks the current Spotify user off by restarting the daemon.
    """
    print("--- KICKING SPOTIFY USER ---")
    try:
        # We assume spotifyd is running as a user service
        subprocess.run(["pkill", "spotifyd"], check=False)
        time.sleep(1)  # Give it a moment to shut down
        subprocess.Popen(["spotifyd"])
    except Exception as e:
        print(f"Error restarting spotifyd: {e}")

def enter_pairing_mode():
    """
    Puts the Bluetooth adapter into pairing mode.
    """
    print("--- ENTERING PAIRING MODE ---")
    try:
        # Using bluetoothctl to make the device discoverable and pairable
        subprocess.run(["bluetoothctl", "disconnect"], check=False)
        subprocess.run(["bluetoothctl", "power", "on"], check=False)
        subprocess.run(["bluetoothctl", "discoverable", "on"], check=False)
        subprocess.run(["bluetoothctl", "pairable", "on"], check=False)
        subprocess.run(["bluetoothctl", "agent", "on"], check=False)
        print("Bluetooth is now in pairing mode.")
    except Exception as e:
        print(f"Error entering pairing mode: {e}")

def turn_off_bluetooth():
    """
    Turns off the Bluetooth adapter.
    """
    print("--- TURNING OFF BLUETOOTH ---")
    try:
        subprocess.run(["bluetoothctl", "power", "off"], check=False)
        print("Bluetooth has been turned off.")
    except Exception as e:
        print(f"Error turning off Bluetooth: {e}")

def turn_on_bluetooth():
    """
    Turns on the Bluetooth adapter.
    """
    print("--- TURNING ON BLUETOOTH ---")
    try:
        subprocess.run(["bluetoothctl", "power", "on"], check=False)
        print("Bluetooth has been turned on.")
    except Exception as e:
        print(f"Error turning on Bluetooth: {e}")
        
def find_hardware_sink():
    """
    Finds the REAL hardware sink (ignoring Loopback).
    Returns the sink name or None if not found.
    """
    try:
        # List all sinks in short format
        output = subprocess.check_output(["pactl", "list", "short", "sinks"], text=True)
        
        for line in output.splitlines():
            parts = line.split()
            if len(parts) > 1:
                sink_name = parts[1]
                
                # If it's not a loopback, it's likely a DAC
                if "loopback" not in sink_name and "aloop" not in sink_name and "alsa_output" in sink_name and "platform" in sink_name:
                    return sink_name
        
        return None
            
    except Exception as e:
        print(f"Failed to find hardware sink: {e}")
        return None

def set_hardware_volume(volume_percent=50, forced_sink=None):
    """
    Finds the REAL hardware sink (ignoring Loopback) and sets volume.
    """
    try:
        target_sink = find_hardware_sink() if forced_sink is None else forced_sink
        
        if target_sink:
            print(f"Targeting Hardware Sink: {target_sink}")
            # Set volume
            subprocess.run([
                "pamixer", 
                "--sink", target_sink, 
                "--set-volume", str(volume_percent)
            ], check=False)
        else:
            print("Error: Could not find a hardware sink")
            
    except Exception as e:
        print(f"Failed to set hardware volume: {e}")

def scan_wifi_networks():
    """
    Scans for available WiFi networks using 'nmcli' and returns a list of SSIDs.
    """
    try:
        output = subprocess.check_output(["nmcli", "-t", "-f", "SSID,SIGNAL", "dev", "wifi"], text=True)
        ssids = []
        for line in output.splitlines():
            print(line)
            ssid = line.strip().split(":")[0]
            signal = line.strip().split(":")[1]
            if ssid:  # Ignore empty SSIDs
                ssids.append({"ssid": ssid, "level": signal})
        return ssids
    except Exception as e:
        print(f"WiFi Scan Error: {e}")
        return []

def connect_to_wifi(ssid, password):
    """
    Connects to a specified WiFi network using 'nmcli'.
    """
    try:
        print(f"Connecting to WiFi SSID: {ssid}")
        subprocess.run([
            "nmcli", "dev", "wifi", "connect", ssid, "password", password
        ], check=True)
        print("WiFi connection initiated.")
    except Exception as e:
        print(f"WiFi Connection Error: {e}")

def create_temp_hotspot():
    """
    Creates a temporary WiFi hotspot for initial configuration.
    """
    try:
        print("Creating temporary WiFi hotspot 'Nexo-Setup'")
        subprocess.run([
            "nmcli", "dev", "wifi", "hotspot", "ifname", "wlan0", 
            "con-name", "Nexo-Setup", "ssid", "Nexo-Setup", "band", "bg", 
            "password", ""
        ], check=True)
        print("Hotspot 'Nexo-Setup' created.")
    except Exception as e:
        print(f"Hotspot Creation Error: {e}")

def get_current_wifi_ssid():
    """
    Gets the SSID of the currently connected WiFi network.
    Returns the SSID as a string, or None if not connected.
    """
    try:
        output = subprocess.check_output(
            ["iwgetid", "-r"],
            text=True
        ).strip()
        
        if output:
            return output
        else:
            print("Not currently connected to any WiFi network.")
            return None

    except subprocess.CalledProcessError:
        print("Error retrieving current WiFi SSID.")
        return None
    except Exception as e:
        print(f"Failed to get current WiFi SSID: {e}")
        return None
    
def get_track_info_bluetooth():
    """
    Returns a dictionary with current track details.
    """
    info = {
        "title": "Unknown Title",
        "artist": "Unknown Artist",
        "album": "Unknown Album",
        "image_url": "",
        "duration_sec": 0,
        "position_sec": 0,
    }

    try:        
        # Basic Strings
        info["title"] = subprocess.check_output(["playerctl", "metadata", "xesam:title"], text=True).strip()
        info["artist"] = subprocess.check_output(["playerctl", "metadata", "xesam:artist"], text=True).strip()
        info["album"] = subprocess.check_output(["playerctl", "metadata", "xesam:album"], text=True).strip()
        
        # Time (playerctl returns microseconds, so we divide by 1,000,000)
        dur_micro = subprocess.check_output(["playerctl", "metadata", "mpris:length"], text=True).strip()
        info["duration_sec"] = float(dur_micro) / 1000000 if dur_micro else 0

        # Position (seconds), position fails if the player is stopped, so we wrap it
        pos_str = subprocess.check_output(["playerctl", "position"], text=True).strip()
        info["position_sec"] = float(pos_str) if pos_str else 0

    except Exception as e:
        print(f"Metadata Error: {e}")
        
    return info