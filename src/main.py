from gpiozero import Button
from signal import pause
from time import sleep
from threading import Timer, Thread
import uvicorn

import main_controller as controller
import led_helper as leds
import startup
from data_handler import db
from api import app

# Pins
BTN_VOL_DOWN = 13
BTN_PLAY = 6
BTN_VOL_UP = 5

# Settings
HOLD_TIME = 0.6 # Faster hold response
BOUNCE_TIME = 0.05
MULTI_CLICK_SPEED = 0.4 
RAMP_SPEED = 0.1

# Buttons
btn_down = Button(BTN_VOL_DOWN, pull_up=False, hold_time=HOLD_TIME, bounce_time=BOUNCE_TIME)
btn_play = Button(BTN_PLAY, pull_up=False, hold_time=2.0, bounce_time=BOUNCE_TIME)
btn_up = Button(BTN_VOL_UP, pull_up=False, hold_time=HOLD_TIME, bounce_time=BOUNCE_TIME)

# Button handlers

# Volume
def on_vol_held(direction):
    """
    direction: 1 (Up) or -1 (Down)
    """
    button_name = "UP" if direction > 0 else "DOWN"
    print(f"Holding {button_name}")
    
    # Identify which button object to check
    btn_obj = btn_up if direction > 0 else btn_down
    
    controller.state['active_btn'] = button_name
    
    if direction > 0:
        controller.state['up_held'] = True
    else:
        controller.state['down_held'] = True
    
    if controller.state['active_btn'] != button_name:
        return # Another button took over

    controller.sync_volume()
    
    # Loop while user holds the button
    while btn_obj.is_pressed:
        if controller.state['active_btn'] != button_name:
            return # Another button took over
        controller.change_volume(5 * direction) # Change by +/- 5
        leds.ramp_main_led() # Tiny blink for feedback
        sleep(RAMP_SPEED)

def on_vol_press(direction):
    button_name = "UP" if direction > 0 else "DOWN"
    
    controller.state['active_btn'] = button_name
    
    if direction > 0 and controller.state['up_held']:
        controller.state['up_held'] = False
        return # Ignore, was part of hold
    elif direction < 0 and controller.state['down_held']:
        controller.state['down_held'] = False
        return # Ignore, was part of hold
    
    if controller.state['active_btn'] != button_name:
        return # Another button took over
    
    print(f"Tap {button_name}")
    controller.sync_volume()
    controller.change_volume(5 * direction)
    leds.ramp_main_led() # Tiny blink for feedback

# Play button
def execute_play_logic():
    count = controller.state['click_count']
    controller.state['click_count'] = 0 # Reset
    
    if count == 1:
        controller.media_action('play_pause')
    elif count == 2:
        controller.media_action('next')
    elif count >= 3:
        controller.media_action('prev')

def on_play_press():
    # Cancel previous timer
    if controller.state['click_timer']:
        controller.state['click_timer'].cancel()
    
    controller.state['click_count'] += 1
    
    # Start new timer
    t = Timer(MULTI_CLICK_SPEED, execute_play_logic)
    controller.state['click_timer'] = t
    t.start()

def on_play_hold():
    # Long press determines action based on current mode
    if controller.state['current_mode'] == 'spotify':
        controller.media_action('kick_spotify')
    else:
        controller.media_action('pairing_mode')
        sleep(0.5)
        controller.media_action('kick_spotify')

# Bindings

def start_api_server():
    # We run uvicorn programmatically.
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

# Volume Up
btn_up.when_released = lambda: on_vol_press(1)
btn_up.when_held = lambda: on_vol_held(1)

# Volume Down
btn_down.when_released = lambda: on_vol_press(-1)
btn_down.when_held = lambda: on_vol_held(-1)

# Play
btn_play.when_pressed = on_play_press
btn_play.when_held = on_play_hold

# Startup Sequence
sleep(3) # Wait for system to settle
print("--- BOOTING NEXO SPEAKER ---")
print(db.get("volume"))

print("--- DEBUG CONFIG ---")
print(db.get_all())
# Run System Startup (Carla, Spotifyd)
startup.start_up(db.get("volume", 50))

# Sync Initial Volume
controller.sync_volume()

# Start Background Workers (Priority, Mute, Bluetooth)
controller.start_workers()

# Start API Server Thread
# We start this in a daemon thread so it runs in the background
api_thread = Thread(target=start_api_server, daemon=True)
api_thread.start()
print("--- API SERVER STARTED (Port 8000) ---")

print("--- SYSTEM READY ---")

if db.get("wifi")["ssid"] == "":
    print("No WiFi configured. Entering pairing mode.")
    controller.pairing_mode()

pause()