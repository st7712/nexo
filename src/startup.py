import subprocess, json, os
from time import sleep
import system_helper

def link_carla():
    """
    Link Carla input/output sink and source to the virtual cable and DAC respectively.
    """

    hardware_sink = system_helper.find_hardware_sink()
    if not hardware_sink:
        print("Error: Could not find hardware sink.")
        return
    try:
        print("🧹 Removing ALL existing PipeWire links...")

        dump = subprocess.check_output(["pw-dump"], text=True)
        objects = json.loads(dump)

        # Remove ONLY real PipeWire Link objects
        for obj in objects:
            if obj.get("type") == "PipeWire:Interface:Link":
                link_id = str(obj["id"])
                print(f"   Removing link ID: {link_id}")
                subprocess.run(
                    ["pw-link", "-d", link_id],
                    check=False
                )

        sleep(1)

        carla_in = None
        carla_out = None

        for obj in objects:
            props = obj.get("info", {}).get("props", {})
            if props.get("application.name") == "Carla":
                if props.get("media.class") == "Stream/Input/Audio":
                    carla_in = str(obj["id"])
                elif props.get("media.class") == "Stream/Output/Audio":
                    carla_out = str(obj["id"])

        print(f"🎛️  Carla Input Node ID: {carla_in}")
        print(f"🎛️  Carla Output Node ID: {carla_out}")

        if not carla_in or not carla_out:
            print("❌ Could not find Carla nodes — make sure Carla is running!")
            return

        print("🔗 Linking VirtualCable → Carla Input")
        subprocess.run(
            ["pw-link", "VirtualCable", carla_in],
            check=True
        )

        print("🔗 Linking Carla Output → DAC")
        subprocess.run(
            ["pw-link", carla_out, hardware_sink],
            check=True
        )

        print("✅ All links reset and re-created successfully!")

    except Exception as e:
        print(f"Error linking Carla: {e}")

def start_spotifyd(vol=50):
    """
    Starts the spotifyd daemon.
    """
    try:
        subprocess.run(["pkill", "spotifyd"], check=False)
        subprocess.Popen(["spotifyd", "--initial-volume", str(vol)])
        print("spotifyd started.")
    except Exception as e:
        print(f"Error starting spotifyd: {e}")
        
def set_default_sink():
    """
    Sets the default PipeWire sink to the virtual cable.
    """
    try:
        subprocess.run(["pactl", "set-default-sink", "VirtualCable"], check=True)
        print("Default sink set to VirtualCable.")
    except Exception as e:
        print(f"Error setting default sink: {e}")

def start_up(vol=50, max_vol=50):
    """
    Starts up necessary services: Carla and spotifyd.
    """
    print("--- STARTING UP SERVICES ---")
    start_spotifyd(vol)
    print("--- SERVICES STARTED ---")
    sleep(5)  # Give services time to initialize
    link_carla()
    print("Carla connected to virtual cable and DAC.")
    system_helper.set_hardware_volume(max_vol)
    system_helper.set_hardware_volume(max_vol, forced_sink="alsa_output.platform-soc_107c000000_sound.stereo-fallback")
    print(f"Volume set to {max_vol}% on hardware sink.")
    set_default_sink()
    print("--- STARTUP COMPLETE ---")