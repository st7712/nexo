from gpiozero import PWMLED, OutputDevice
from threading import Timer
from time import sleep

# Config
VOLUME_LED_PINS = [16, 12, 25, 24]
MAIN_LED_PIN = 23
MUTE_PIN = 26
LED_TIMEOUT = 3.0

# Setup
vol_leds = [PWMLED(pin) for pin in VOLUME_LED_PINS]
main_led = PWMLED(MAIN_LED_PIN)
fade_timer = None

# Initialize Mute Pin
# active_high=True means: on() sends 3.3V, off() sends 0V.
# Check your amp: Does 3.3V mean MUTE or UNMUTE?
# If 3.3V = Mute, keep active_high=True.
# If 0V = Mute, change to active_high=False.
mute_pin = OutputDevice(MUTE_PIN, active_high=True, initial_value=False)

def set_amp_mute(should_mute):
    """
    Controls the physical mute pin.
    """
    if should_mute:
        if not mute_pin.value: # Only print if changing state
            print("Amp Status: MUTED")
            mute_pin.on()  # Sets pin HIGH (3.3V)
    else:
        if mute_pin.value:
            print("Amp Status: LIVE")
            mute_pin.off() # Sets pin LOW (0V)

def _turn_off_vol_leds():
    """Internal helper to dim LEDs."""
    for led in vol_leds:
        led.off()

def update_volume_display(volume_percent):
    """Lights up the bar based on volume %."""
    global fade_timer
    
    # Reset the auto-off timer
    if fade_timer is not None:
        fade_timer.cancel()

    vol_fraction = volume_percent / 100.0
    num_leds = len(vol_leds)
    
    for i, led in enumerate(vol_leds):
        segment_start = i / num_leds
        segment_end = (i + 1) / num_leds
        
        if vol_fraction >= segment_end:
            led.value = 1.0
        elif vol_fraction <= segment_start:
            led.value = 0.0
        else:
            led.value = (vol_fraction - segment_start) / (1.0 / num_leds)

    # Start new timer
    fade_timer = Timer(LED_TIMEOUT, _turn_off_vol_leds)
    fade_timer.start()

def ramp_main_led(duration=0.1, steps=50):
    """Breathes the main LED once."""
    step_time = duration / steps
    
    # Ramp Up
    for i in range(0, steps + 1):
        main_led.value = i / steps
        sleep(step_time)
    # Ramp Down
    for i in range(steps, -1, -1):
        main_led.value = i / steps
        sleep(step_time)
    main_led.off()