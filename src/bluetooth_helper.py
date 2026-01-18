import asyncio
from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
from dbus_next import Variant

async def _get_bus():
    """Connect to the System Bus."""
    return await MessageBus(bus_type=BusType.SYSTEM).connect()

async def _get_bluez_objects(bus):
    """
    Fetch all managed objects from BlueZ (Devices, Transports, Adapters).
    This replaces the slow 'bluetoothctl' parsing.
    """
    # Get the ObjectManager
    introspection = await bus.introspect("org.bluez", "/")
    obj_manager = bus.get_proxy_object("org.bluez", "/", introspection)
    iface = obj_manager.get_interface("org.freedesktop.DBus.ObjectManager")
    
    # Return dictionary of all objects
    return await iface.call_get_managed_objects()

async def _find_transport_path(bus):
    """Finds the first active MediaTransport1 (A2DP Audio Stream)."""
    objects = await _get_bluez_objects(bus)
    
    for path, interfaces in objects.items():
        if "org.bluez.MediaTransport1" in interfaces:
            # Found an audio transport
            return path
    return None

async def _set_volume_async(volume_percent):
    """Async implementation of setting volume."""
    bus = await _get_bus()
    try:
        transport_path = await _find_transport_path(bus)
        if not transport_path:
            return

        # Convert 0-100 to 0-127 (BlueZ uint16 scale)
        vol_clamped = max(0, min(100, volume_percent))
        bt_volume = int((vol_clamped / 100) * 127)

        # Get the Properties interface for this specific transport
        introspection = await bus.introspect("org.bluez", transport_path)
        proxy = bus.get_proxy_object("org.bluez", transport_path, introspection)
        props = proxy.get_interface("org.freedesktop.DBus.Properties")

        # Set the Volume
        await props.call_set("org.bluez.MediaTransport1", "Volume", Variant('q', bt_volume))
        print(f"Bluetooth Volume set to {bt_volume}/127 (path: {transport_path})")
        
    except Exception as e:
        print(f"DBus Set Error: {e}")
    finally:
        # Close connection to free resources
        bus.disconnect()

async def _get_volume_async():
    """Async implementation of getting volume."""
    bus = await _get_bus()
    try:
        transport_path = await _find_transport_path(bus)
        if not transport_path:
            return None

        # Get Property
        introspection = await bus.introspect("org.bluez", transport_path)
        proxy = bus.get_proxy_object("org.bluez", transport_path, introspection)
        props = proxy.get_interface("org.freedesktop.DBus.Properties")

        # Read Volume
        bt_volume = await props.call_get("org.bluez.MediaTransport1", "Volume")
        
        # Convert back to percent (bt_volume is a Variant, .value gets the int)
        return int((bt_volume.value / 127) * 100)

    except Exception as e:
        print(f"DBus Get Error: {e}")
        return None
    finally:
        bus.disconnect()

async def _get_connected_devices_async():
    """Async scan for connected devices (No more subprocess!)."""
    bus = await _get_bus()
    connected_macs = []
    try:
        objects = await _get_bluez_objects(bus)
        
        for path, interfaces in objects.items():
            # Check if it is a Device
            if "org.bluez.Device1" in interfaces:
                device_props = interfaces["org.bluez.Device1"]
                
                # Check 'Connected' property (It comes as a Variant)
                is_connected = device_props.get("Connected", Variant('b', False)).value
                
                if is_connected:
                    # The Address is also a property
                    address = device_props.get("Address", Variant('s', "")).value
                    if address:
                        connected_macs.append(address)
                        
    except Exception as e:
        print(f"DBus Device Scan Error: {e}")
    finally:
        bus.disconnect()
        
    return connected_macs

async def _disconnect_device_async(mac_address):
    """Disconnects a device using DBus methods."""
    bus = await _get_bus()
    try:
        objects = await _get_bluez_objects(bus)
        
        for path, interfaces in objects.items():
            if "org.bluez.Device1" in interfaces:
                props = interfaces["org.bluez.Device1"]
                addr = props.get("Address", Variant('s', "")).value
                
                # Found the target device
                if addr == mac_address:
                    print(f"Found device at {path}, disconnecting...")
                    introspection = await bus.introspect("org.bluez", path)
                    device = bus.get_proxy_object("org.bluez", path, introspection)
                    interface = device.get_interface("org.bluez.Device1")
                    
                    await interface.call_disconnect()
                    print(f"Disconnected {mac_address}")
                    return

    except Exception as e:
        print(f"DBus Disconnect Error: {e}")
    finally:
        bus.disconnect()


# Synchronous wrappers

def set_bluetooth_volume(volume_percent):
    """Sets volume of current transport (0-100)."""
    asyncio.run(_set_volume_async(volume_percent))

def get_bluetooth_volume():
    """Gets volume of current transport (0-100). Returns None if not playing."""
    return asyncio.run(_get_volume_async())

def get_connected_devices():
    """Returns list of MAC addresses of currently connected devices."""
    return asyncio.run(_get_connected_devices_async())

def disconnect_device(mac_address):
    """Force disconnects a specific MAC address."""
    asyncio.run(_disconnect_device_async(mac_address))