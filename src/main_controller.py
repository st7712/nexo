from threading import Timer, Thread
from time import sleep
import subprocess

import spotify_helper as spotify
import led_helper as leds
import bluetooth_helper as bluetooth
import system_helper as system
import data_handler
from carla_osc import set_loudness_contour_eq

# --- SHARED STATE ---
# This dictionary lives here. Anyone importing this file shares this state
# (as long as they run in the same process).
state = {
    'volume': data_handler.db.get("volume", 50),
    'max_volume': data_handler.db.get("max_volume", 50),
    'current_mode': 'spotify', # 'spotify' or 'bluetooth'
    'bt_owner_mac': None,
    'click_count': 0,
    'click_timer': None,
    'down_held': False,
    'up_held': False,
    'active_btn': None,
}

LOUDNESS_SLOPES = {
    40: 0.00394,
    63: 0.00521,
    100: 0.00372,
}

CONNECT_SOUND_PATH = f"{data_handler.db.get('root_path')}/assets/sounds/connect.wav"

# volume functions
def sync_volume():
    """Syncs internal state with Spotify's actual volume."""
    state['volume'] = spotify.get_volume()
    print(f"Synced volume: {state['volume']}%")

def change_volume(amount, override=False):
    """
    Main volume function. Called by Buttons OR API.
    """
    old_volume = state['volume']
    
    # Update State
    if override:
        new_volume = max(0, min(100, amount))
    else:
        new_volume = max(0, min(100, state['volume'] + amount))
        
    state['volume'] = new_volume
    
    if new_volume > old_volume:
        # Drop EQ first to prevent clipping
        update_loudness_contour(new_volume)
        _apply_hardware_volume(new_volume)
    elif new_volume < old_volume:
        # Drop Amp volume first to prevent bass spikes
        _apply_hardware_volume(new_volume)
        update_loudness_contour(new_volume)

    # Visual Feedback and save to DB
    leds.update_volume_display(state['volume'])
    data_handler.db.set("volume", state['volume'])

def _apply_hardware_volume(vol):
    """Helper function to apply volume changes to the correct output."""
    if state['current_mode'] == 'bluetooth':
        bluetooth.set_bluetooth_volume(vol)
        print(f"Vol (BT): {vol}")
    else:
        spotify.set_volume(vol)
        print(f"Vol (Spotify): {vol}")

def get_volume():
    sync_volume() # Ensure we have the latest volume before returning
    return state['volume']

# media control functions
def media_action(action):
    """
    Unified media control.
    action: 'play_pause', 'next', 'prev', 'kick_spotify', 'pairing_mode'
    """
    print(f"Controller: Executing {action}")
    
    if action == 'play_pause':
        spotify.play_pause()
        leds.ramp_main_led(0.1)
        update_mute_status() # Check immediately
        
    elif action == 'next':
        spotify.next_track()
        leds.ramp_main_led(0.1)
        sleep(0.1)
        leds.ramp_main_led(0.1)
        
    elif action == 'prev':
        spotify.previous_track()
        leds.ramp_main_led(0.1)
        sleep(0.1)
        leds.ramp_main_led(0.1)
        sleep(0.1)
        leds.ramp_main_led(0.1)

    elif action == 'kick_spotify':
        # Force Restart Spotifyd
        leds.ramp_main_led(0.1)
        sleep(0.1)
        leds.ramp_main_led(0.1)
        system.restart_spotifyd()
        
    elif action == 'pairing_mode':
        # Force Bluetooth Pairing
        leds.ramp_main_led(1.0) # Long flash
        state['bt_owner_mac'] = None
        system.enter_pairing_mode()
        # Flash to indicate searching
        for _ in range(5):
            leds.ramp_main_led(0.1)
            sleep(0.1)

# background workers
def update_mute_status(status=None):
    """Checks if we should mute the Amp."""
    print(f"Updating Amp Mute Status...{status}")
    try:
        if status is None:
            status = subprocess.check_output(["playerctl", "status"], text=True).strip()
        if status == "Playing":
            leds.set_amp_mute(False)
        else:
            leds.set_amp_mute(True)
    except:
        leds.set_amp_mute(True)

global status

def background_worker_loop():
    """
    The main brain loop. Checks priority, muting, and bluetooth security.
    """
    hardware_sink = system.find_hardware_sink()
    
    while True:
        # Check Spotify Status
        spotify_active, status = system.is_spotify_active()
        
        if (not status):
            status = "unknown"
        
        # Handle Amp Mute
        # To save another request to the terminal, we pass the status we already have
        update_mute_status(status)
        
        # If paused, start a timer to kick after 5 minutes
        if spotify_active and status == "Paused" and 'spotify_disconnect_timer' not in globals():
            print("Spotify is paused. Starting disconnect timer.")
            
            global spotify_disconnect_timer
            
            spotify_disconnect_timer = Timer(300, media_action, args=('kick_spotify',))
            
            spotify_disconnect_timer.start()
        elif status != "Paused" and 'spotify_disconnect_timer' in globals():
            # Cancel any existing timer
            try:
                print("Cancelling disconnect timer.")
                spotify_disconnect_timer.cancel()
                del spotify_disconnect_timer
            except Exception:
                pass

        # Priority Switching
        # Spotify just started playing -> Kill BT
        if spotify_active and state['current_mode'] == 'bluetooth':
            print(">>> Priority: Spotify took over.")
            system.turn_off_bluetooth()
            state['current_mode'] = 'spotify'
            system.play_sound(CONNECT_SOUND_PATH, volume=(get_volume() * 300))  # Scale 0-100 to 0-65536
            leds.ramp_main_led(1.0) # Feedback

        # Spotify stopped -> Restore BT
        elif not spotify_active and state['current_mode'] == 'spotify':
            print(">>> Priority: Spotify gone. Restoring BT.")
            system.turn_on_bluetooth()
            state['current_mode'] = 'bluetooth'
            state['bt_owner_mac'] = None # Open for connections
            leds.ramp_main_led(1.0) # Feedback

        # Bluetooth Security
        if state['current_mode'] == 'bluetooth':
            _bluetooth_bouncer()

        system.set_hardware_volume(state['max_volume'], forced_sink=hardware_sink)

        sleep(2)

def _bluetooth_bouncer():
    """Ensures only 1 person connects and trusts them."""
    try:
        connected = bluetooth.get_connected_devices()

        # New Connection -> Lock it
        if state['bt_owner_mac'] is None and len(connected) > 0:
            state['bt_owner_mac'] = connected[0]
            print(f"BT Locked to: {state['bt_owner_mac']}")

            # Make invisible so nobody else tries to pair
            subprocess.run(["bluetoothctl", "discoverable", "off"], check=False)
            subprocess.run(["bluetoothctl", "pairable", "off"], check=False)

        # Owner Left -> Unlock
        elif state['bt_owner_mac'] and state['bt_owner_mac'] not in connected:
            state['bt_owner_mac'] = None
            print("BT Unlocked.")
            
            # Re-open the doors for anyone
            subprocess.run(["bluetoothctl", "discoverable", "on"], check=False)
            subprocess.run(["bluetoothctl", "pairable", "on"], check=False)

        # Intruder -> Kick
        if len(connected) > 1:
            print(f"Too many devices! Enforcing limit...")
            for mac in connected:
                if mac != state['bt_owner_mac']:
                    bluetooth.disconnect_device(mac)
                    
    except Exception as e:
        print(f"Enforcer Error: {e}")

def volume_worker_loop():
    """Polls playerctl at 10Hz to catch external volume changes instantly."""
    
    last_known_volume = get_volume()
    
    while True:
        try:
            result = subprocess.run(
                ["playerctl", "volume"], 
                capture_output=True, 
                text=True, 
                timeout=0.2
            )
            if result.returncode == 0 and result.stdout.strip():
                external_vol_float = float(result.stdout.strip())
                current_vol = int(external_vol_float * 100)
                
                if current_vol != last_known_volume:
                    state['volume'] = current_vol
                    update_loudness_contour(current_vol)
                    
                    leds.update_volume_display(current_vol)
                    data_handler.db.set("volume", current_vol)
                    
                    last_known_volume = current_vol
                    
        except subprocess.TimeoutExpired:
            pass # DBus was busy, just try again next loop
        except ValueError:
            pass # playerctl returned something weird (not a number)
        except Exception as e:
            # playerctl might return an error if no players are active. Just ignore.
            pass
            
        sleep(0.1)

def start_workers():
    t = Thread(target=background_worker_loop, daemon=True)
    t.start()
    
    v = Thread(target=volume_worker_loop, daemon=True)
    v.start()

def get_full_system_state():
    """
    Compiles the complete state of the speaker for the App.
    """
    sync_volume()  # Ensure volume is up to date
    # Get Playback Data
    if state['current_mode'] == 'spotify':
        track_data = spotify.get_track_info()
    else:
        track_data = system.get_track_info_bluetooth()

    # Combine with System State
    full_state = {
        "volume": get_volume(),
        "mode": state['current_mode'],
        "track": track_data,
    }

    return full_state

def get_partial_system_state():
    """
    Returns a minimal state for quick checks.
    """
    sync_volume()  # Ensure volume is up to date
    partial_state = {
        "volume": get_volume(),
        "status": system.is_spotify_active()[1],
        "position": spotify.get_track_position(),
    }
    return partial_state

# system functions

def scan_wifi_networks():
    """Scans for available WiFi networks and returns a list of SSIDs."""
    networks = system.scan_wifi_networks()
    return networks

def connect_to_wifi(ssid, password):
    """Connects to a specified WiFi network."""
    system.connect_to_wifi(ssid, password)
    
def pairing_mode():
    """Enters speaker pairing mode."""
    system.create_temp_hotspot()
    
def update_loudness_contour(current_volume):
    """Updates the Loudness Contour EQ settings."""
    vol_drop = 80 - current_volume # Calculate how much the volume is reduced from max
    
    eq_settings = {}
    
    for freq, slope in LOUDNESS_SLOPES.items():
        osc_val = 0.5 + (slope * vol_drop) # Start at 0.5 (flat) and adjust based on volume drop
        osc_val = max(0.5, min(1.0, osc_val)) # Clamp between 0.5 and 1
        eq_settings[int(freq)] = round(osc_val, 3) # Round for cleaner OSC messages
        
    set_loudness_contour_eq(eq_settings)
    
    print(f"Loudness Contour Updated: {eq_settings}")