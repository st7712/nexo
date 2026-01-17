import led_helper as leds
import system_helper as system
from time import sleep

leds.set_amp_mute(True)  # Mute the speaker amplifier

system.set_hardware_volume(0) # Set hardware volume to 0%
system.set_hardware_volume(0, forced_sink="alsa_output.platform-soc_107c000000_sound.stereo-fallback") # Specific sink for Pi DAC+
sleep(1) # Give time for volume to settle