from threading import Timer, Thread
from time import sleep
import subprocess

import spotify_helper as spotify
import led_helper as leds
import bluetooth_helper as bluetooth
import system_helper as system
import data_handler

# --- SHARED STATE ---
# This dictionary lives here. Anyone importing this file shares this state
# (as long as they run in the same process).
state = {
    'volume': 50,
    'current_mode': 'spotify', # 'spotify' or 'bluetooth'
    'bt_owner_mac': None,
    'click_count': 0,
    'click_timer': None,
    'down_held': False,
    'up_held': False,
    'active_btn': None,
}

CONNECT_SOUND_PATH = "/home/pi/nexo/src/connect.wav"

# volume functions
def sync_volume():
    """Syncs internal state with Spotify's actual volume."""
    state['volume'] = spotify.get_volume()
    print(f"Synced volume: {state['volume']}%")

def change_volume(amount, override=False):
    """
    Main volume function. Called by Buttons OR API.
    """
    # Update State
    if override:
        state['volume'] = amount
    else:
        state['volume'] = max(0, min(100, state['volume'] + amount))
    
    # Update Hardware (Spotify or Bluetooth)
    if state['current_mode'] == 'bluetooth':
        bluetooth.set_bluetooth_volume(state['volume'])
        print(f"Vol (BT): {state['volume']}")
    else:
        spotify.set_volume(state['volume'])
        print(f"Vol (Spotify): {state['volume']}")

    # Visual Feedback
    leds.update_volume_display(state['volume'])
    
    # Save to DB
    data_handler.db.set("volume", state['volume'])

def get_volume():
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
            system.play_sound(CONNECT_SOUND_PATH)
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

def start_workers():
    t = Thread(target=background_worker_loop, daemon=True)
    t.start()

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
        "volume": state['volume'],
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
        "volume": state['volume'],
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