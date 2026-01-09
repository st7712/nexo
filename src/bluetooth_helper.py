import dbus, subprocess

def get_target_transport():
    """
    Scans for ANY active Bluetooth Audio Transport and sets its volume.
    Maps 0-100% (Input) to 0-127 (BlueZ Scale).
    """
    try:
        # Connect to System Bus
        bus = dbus.SystemBus()
        
        # Get the Object Manager (The "Master List" of all BlueZ objects)
        manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()

        target_transport = None

        # Iterate through all objects to find one that is a "MediaTransport1"
        for path, interfaces in objects.items():
            if "org.bluez.MediaTransport1" in interfaces:
                
                # Check if this transport is connected/active (usually checks for 'State')
                # But typically if it exists, it's the one we want.
                # If you have multiple phones connected, this grabs the first one it finds.
                target_transport = path
                break
        
        return target_transport, bus

    except Exception as e:
        print(f"Failed to get Transport: {e}")
        return None, None

def set_bluetooth_volume(volume_percent):
    """
    set the bluetooth volume of the current connected device

    Args:
        volume_percent (int): The desired volume level as a percentage (0-100).
    """
    target_transport, bus = get_target_transport()

    if target_transport:
        # Convert 0-100 scale to 0-127 scale
        # Ensure volume is clamped between 0 and 100 first
        volume_percent = max(0, min(100, volume_percent))
        bt_volume = int((volume_percent / 100) * 127)

        # Set the Property
        transport_obj = bus.get_object("org.bluez", target_transport)
        props = dbus.Interface(transport_obj, "org.freedesktop.DBus.Properties")
        
        # Signature: Interface, Property Name, Value (UInt16)
        props.Set("org.bluez.MediaTransport1", "Volume", dbus.UInt16(bt_volume))
        
        print(f"Bluetooth Volume set to {bt_volume}/127")
    else:
        # This is normal if Bluetooth is not connected.
        pass

def get_bluetooth_volume():
    """
    get the bluetooth volume of the current connected device
    
    Returns:
        int: The current volume level as a percentage (0-100), or None if no device is connected.
    """
    target_transport, bus = get_target_transport()

    if target_transport:
        transport_obj = bus.get_object("org.bluez", target_transport)
        props = dbus.Interface(transport_obj, "org.freedesktop.DBus.Properties")
        
        bt_volume = props.Get("org.bluez.MediaTransport1", "Volume")
        
        # Convert 0-127 scale to 0-100 scale
        volume_percent = int((bt_volume / 127) * 100)
        
        print(f"Bluetooth Volume is {bt_volume}/127 ({volume_percent}%)")
        
        return volume_percent
    else:
        return None

def get_connected_devices():
    """
    Returns a list of MAC addresses of currently CONNECTED devices.
    """
    connected = []
    try:
        # Ask bluetoothctl for info on all available devices
        # We filter for "Connected: yes"
        # This is a bit heavy, so we use a faster piped command
        output = subprocess.check_output("bluetoothctl devices | cut -f2 -d' ' | while read uuid; do bluetoothctl info $uuid; done", shell=True, text=True)

        current_mac = None
        for line in output.splitlines():
            if line.startswith("Device"):
                current_mac = line.split()[1]
            if "Connected: yes" in line and current_mac:
                connected.append(current_mac)
    except Exception:
        # Fallback or simple error handling
        pass
    return connected

def disconnect_device(mac_address):
    """
    Kicks a specific device off.
    """
    print(f"--- Kicking Device: {mac_address} ---")
    subprocess.run(["bluetoothctl", "disconnect", mac_address], check=False)