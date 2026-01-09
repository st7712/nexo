import subprocess

def get_volume():
    """Asks spotifyd for current volume (returns int 0-100)."""
    try:
        # playerctl returns float 0.0 to 1.0, we convert to int 0-100
        output = subprocess.check_output(["playerctl", "volume"], text=True).strip()
        if output:
            return int(round(float(output) * 100))
    except Exception:
        pass
    return 50 # fallback volume

def set_volume(vol_percent):
    """Sets volume (0-100)."""
    print(f"Setting Spotify volume to: {vol_percent}%")
    try:
        # Convert 0-100 back to 0.0-1.0
        val = max(0, min(100, vol_percent)) / 100.0
        subprocess.run(["playerctl", "volume", str(val)], check=False)
    except Exception as e:
        print(f"Error setting volume: {e}")

def play_pause():
    subprocess.run(["playerctl", "play-pause"], check=False)

def next_track():
    print(">> Skipping Track")
    subprocess.run(["playerctl", "next"], check=False)

def previous_track():
    print("<< Previous Track")
    subprocess.run(["playerctl", "previous"], check=False)
    
def get_track_info():
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
        # We can fetch specific metadata keys using format strings
        # This is faster than parsing a huge JSON block
        
        # Basic Strings
        info["title"] = subprocess.check_output(["playerctl", "metadata", "xesam:title"], text=True).strip()
        info["artist"] = subprocess.check_output(["playerctl", "metadata", "xesam:artist"], text=True).strip()
        info["album"] = subprocess.check_output(["playerctl", "metadata", "xesam:album"], text=True).strip()
        info["image_url"] = subprocess.check_output(["playerctl", "metadata", "mpris:artUrl"], text=True).strip()
        
        # Time (playerctl returns microseconds, so we divide by 1,000,000)
        dur_micro = subprocess.check_output(["playerctl", "metadata", "mpris:length"], text=True).strip()
        info["duration_sec"] = float(dur_micro) / 1000000 if dur_micro else 0

        # Position (seconds), position fails if the player is stopped, so we wrap it
        pos_str = subprocess.check_output(["playerctl", "position"], text=True).strip()
        info["position_sec"] = float(pos_str) if pos_str else 0

    except Exception as e:
        print(f"Metadata Error: {e}")
        
    return info

def get_track_position():
    """Returns current track position in seconds."""
    try:
        pos_str = subprocess.check_output(["playerctl", "position"], text=True).strip()
        return round(float(pos_str)) if pos_str else 0
    except Exception:
        return 0