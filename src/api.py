from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data_handler import db
import main_controller as controller
import carla_osc as carla

app = FastAPI(title="Nexo Speaker API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # We can't really restrict to one IP cause of the mobile app
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

# Pydantic data models
# Defines the shape of data expected in requests
class VolumeRequest(BaseModel):
    volume: int

class EQRequest(BaseModel):
    band_type: str
    preset: str # Preset number 1-6 from app

class PlaybackRequest(BaseModel):
    value: str  # e.g., "play", "pause", "next", "previous"
    
class NetworkConnectRequest(BaseModel):
    ssid: str
    password: str

# Api endpoints

@app.get("/")
def read_root():
    return {"status": "online", "name": db.get("device_name"), "id": db.get("device_id"), "master": True}

# Settings endpoints
@app.get("/settings")
def get_settings():
    return db.get_all()

@app.post("/settings/name")
def update_name(name: str):
    db.set("device_name", name)
    return {"status": "updated", "name": name}

# Control endpoints

# We use BackgroundTasks so the API returns "OK" immediately,
# while the actual hardware work happens in the background.

def _hardware_set_volume(vol):
    """Placeholder: Call your actual main.py logic here"""
    print(f"HARDWARE: Setting volume to {vol}%")
    controller.change_volume(vol, override=True)

def _hardware_set_eq(band_type, preset):
    """Placeholder: Call your actual EQ setting logic here"""
    print(f"HARDWARE: Setting EQ {band_type} to preset {preset}")
    print(db.get("eq_presets"))
    for freq, gain in db.get("eq_presets")[band_type][str(abs(preset))].items():
        if preset < 0:
            carla.set_eq_gain(int(freq), (1 - gain))  # Invert gain for negative presets
        else:
            carla.set_eq_gain(int(freq), gain)
    # Save current EQ to DB
    db.set(f"current_eq_{band_type}", preset)

@app.post("/control/volume")
async def set_volume(req: VolumeRequest, background_tasks: BackgroundTasks):
    if req.volume < 0 or req.volume > 100:
        raise HTTPException(status_code=400, detail="Volume must be 0-100")
    
    # Trigger hardware change
    background_tasks.add_task(_hardware_set_volume, req.volume)
    
    return {"status": "processing", "target_volume": req.volume}

@app.post("/control/playback")
async def control_playback(req: PlaybackRequest):
    if req.value not in ["play_pause", "next", "prev"]:
        raise HTTPException(status_code=400, detail="Invalid playback action")
    print(f"HARDWARE: Media Action -> {req.value}")
    controller.media_action(req.value)
    return {"status": "executed", "action": req.value}

@app.post("/control/eq")
def set_eq(req: EQRequest, background_tasks: BackgroundTasks):
    print(f"HARDWARE: Setting EQ {req.band_type} to preset {req.preset}")
    try: 
        req.preset = int(req.preset)
    except ValueError:
        raise HTTPException(status_code=400, detail="preset must be an integer between -6 and 6")
    if req.band_type not in ["bass", "treble"]:
        raise HTTPException(status_code=400, detail="band_type must be 'bass' or 'treble'")
    if req.preset < -6 or req.preset > 6:
        raise HTTPException(status_code=400, detail="preset must be between -6 and 6")
    background_tasks.add_task(_hardware_set_eq, req.band_type, req.preset)
    return {"status": "processing", "band_type": req.band_type, "preset": f"{req.band_type}-{req.preset}"}

@app.get("/control/eq")
def get_current_eq():
    current_eq_bass = db.get("current_eq_bass")
    current_eq_treble = db.get("current_eq_treble")
    return {"bass": current_eq_bass, "treble": current_eq_treble}

@app.post("/control/eq/status")
def set_eq_status(value: str, background_tasks: BackgroundTasks):
    """Sets the current EQ status without changing the EQ preset"""
    if value not in ["on", "off"]:
        raise HTTPException(status_code=400, detail="Value must be 'on' or 'off'")
    is_on = True if value == "on" else False
    db.set("eq_enabled", is_on)
    background_tasks.add_task(_hardware_set_eq, "bass", db.get("current_eq_bass") if is_on else 0)
    background_tasks.add_task(_hardware_set_eq, "treble", db.get("current_eq_treble") if is_on else 0)
    return {"status": "updated", "eq_enabled": is_on}

@app.get("/status/state")
def get_system_state():
    """Returns current track info from main_controller."""
    state_info = controller.get_full_system_state()
    return state_info

@app.get("/status/partial_state")
def get_partial_system_state():
    """Returns current track position info."""
    partial_info = controller.get_partial_system_state()
    return partial_info

@app.get("/network/ssid")
def get_network_ssid():
    """Returns the current connected WiFi SSID."""
    ssid = db.get("wifi")["ssid"]
    return {"ssid": ssid}

@app.get("/network/scan")
def scan_networks():
    """Scans for available WiFi networks."""
    networks = controller.scan_wifi_networks()
    print(f"Scanned Networks: {networks}")
    return {"networks": networks}

@app.post("/network/connect")
def connect_network(req: NetworkConnectRequest, background_tasks: BackgroundTasks):
    """Connects to a specified WiFi network."""
    if not req.ssid or not req.password:
        raise HTTPException(status_code=400, detail="SSID and password are required")
    background_tasks.add_task(controller.connect_to_wifi, req.ssid, req.password)
    db.set("wifi", {"ssid": req.ssid, "password": req.password})
    return {"status": "connecting", "ssid": req.ssid}

@app.post("/control/local/volume")
def set_local_volume(req: VolumeRequest, background_tasks: BackgroundTasks):
    """Sets the local hardware volume (e.g., amplifier) directly."""
    if req.volume < 0 or req.volume > 100:
        raise HTTPException(status_code=400, detail="Volume must be 0-100")
    print(f"HARDWARE: Setting LOCAL volume to {req.volume}%")
    background_tasks.add_task(_hardware_set_volume, req.volume)
    return {"status": "executed", "local_volume": req.volume}

@app.post("/control/local/mute")
def set_local_mute(value: str, background_tasks: BackgroundTasks):
    """Mutes or unmutes the local hardware volume directly."""
    if value not in ["mute", "unmute"]:
        raise HTTPException(status_code=400, detail="Value must be 'mute' or 'unmute'")
    mute = True if value == "mute" else False
    if mute:
        print("HARDWARE: Muting local volume")
        background_tasks.add_task(_hardware_set_volume, 0)
    else:
        print("HARDWARE: Unmuting local volume")
        background_tasks.add_task(_hardware_set_volume, 100)
    return {"status": "executed", "mute": mute}

@app.post("/settings/reset")
def reset_settings():
    """Resets all settings to default."""
    db.reset_to_default()
    return {"status": "reset_to_default"}