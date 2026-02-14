<div align="center">
  <img src="https://stito.eu.org/assets/img/NexoLogoWhite.png" alt="Nexo Logo" width="200px" />
  <h1>Nexo Smart Speaker</h1>
  
  <p>
    <strong>A DIY, open-source smart speaker built on Raspberry Pi.</strong>
  </p>

  <p>
    <a href="https://github.com/st7712/nexo?tab=readme-ov-file#features">Features</a> •
    <a href="https://github.com/st7712/nexo?tab=readme-ov-file#installation">Installation</a> •
    <a href="https://github.com/st7712/nexo?tab=readme-ov-file#hardware">Hardware</a> •
    <a href="https://github.com/st7712/nexo?tab=readme-ov-file#configuration">Configuration</a> •
    <a href="https://discord.com/users/stitoo">Support</a>
  </p>

  ![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
  ![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)
</div>

---

## About
**Nexo** converts a standard Raspberry Pi into a high-fidelity, network-aware smart speaker. Unlike standard Bluetooth speakers, Nexo acts as a central audio hub that intelligently manages input sources.

It runs a headless Python controller that seamlessly switches between **Spotify Connect** (High Quality WiFi streaming) and **Bluetooth** (for guests/offline use). It also features professional-grade DSP (Digital Signal Processing) via **Carla**, allowing for active crossover tuning, EQ, and room correction directly on the device.

## Features

- **Priority Audio Switching**: Automatically switches inputs. Playing Spotify pauses Bluetooth; stopping Spotify wakes Bluetooth back up.
- **Smart Connectivity**:
  - **Spotify Connect**: Stream directly from the cloud.
  - **Bluetooth 5.0**: High-quality A2DP sink with intelligent pairing.
- **Hardware Control**: Sonos-inspired play/pause/skip middle button, with side volume buttons, and status LEDs.
- **Pro-Audio Engine**: Uses [PipeWire](https://pipewire.org/) & [Carla](https://kx.studio/Applications:Carla) for low-latency audio processing and equalization.
- **API Controlled**: Built-in FastAPI backend for mobile app integration and smart home control.
- **Persistent Settings**: Remembers volume and EQ profiles across reboots.
- **Pretty good frequency response**: The exact speaker with the listed parts has a decent frequency response:
![nexo curve](https://github.com/user-attachments/assets/7010921e-263e-4ea3-85f0-3655d68c097b)
> Measured with an uncalibrated microphone with poor high frequency coverage


## Installation

**Prerequisites:**
* Raspberry Pi 3B+, 4 or 5 (Recommended)
* Raspberry Pi OS (Bookworm or newer)

**Installer:**
SSH into your Raspberry Pi and run this command. It will install dependencies, compile Spotifyd, and configure system services automatically.

```bash
sudo apt update && sudo apt install -y git && \
git clone https://github.com/st7712/nexo.git && \
cd nexo && chmod +x install.sh && sudo ./install.sh
```

*Note: The installation may take 10-20 minutes depending on your Pi model (compiling Rust dependencies takes time).*

## Usage

### Physical Controls

| Button Input | Action |
| --- | --- |
| **Vol + / -** (Click for 5% / Hold for 10% continuous) | Changes Volume (Synchronized with Spotify/Bluetooth) |
| **Play (1 Click)** | Play / Pause |
| **Play (2 Clicks)** | Next Track |
| **Play (3 Clicks)** | Previous Track |
| **Play (Hold)** | **Force Pairing Mode / Restarts Spotify** (Disconnects current user from Bluetooth if Bluetooth active and also restarts Spotifyd) |

### API / App

The speaker hosts a local API at `http://<raspberry-pi-ip>:8000`. You can control playback, volume, EQ, and fetch metadata via REST.

## Hardware

Nexo is designed to work with generic I2S DACs (like HiFiBerry, Pimoroni, or generic PCM5102).

- **[View my Full Hardware Docs](https://github.com/st7712/nexo/blob/main/hardware/README.md)** 
- **[View my Bill of Materials (BOM)](https://github.com/st7712/nexo/blob/main/hardware/bom.md)**
- **[View my Full Hardware Assembly Guide](https://github.com/st7712/nexo/blob/main/hardware/assembly_guide.md)** 

## Configuration

Advanced users can tweak GPIO pins and audio settings.

1. **System Config**: Edit `assets/configs/nexo_config.json` (created after first run) or `DEFAULT_CONFIG ` in `src/data_handler.py` directly.
* Change `device_name` to whatever name you'd like
* Set `sounds` whether or not you want to have sound effects
* Modify `eq_presets` to change the equalizer presets to your liking
* Edit `max_volume` to match your specific amplifier
* ~Switch `master` if you'd like to have the specific speaker as just a listener, not a broadcaster~ (multi-room is in development)

2. **Pin Layout**: Edit `src/led_helper.py` if you use different GPIO pins for LEDs and `src/main.py` for buttons.
3. **Specific Carla settings**: Edit `src/carla_osc.py` if you somehow changed the Carla config and are using different plugins.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

1. Fork the repo.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes.
4. Push to the branch.
5. Open a Pull Request.

## Used Projects

* [Spotifyd](https://github.com/Spotifyd/spotifyd) - Lightweight Spotify Client
* [Carla](https://kx.studio/Applications:Carla) - Audio Plugin Host
* [FastAPI](https://fastapi.tiangolo.com/) - Modern Python Web Framework
* [Linux Studio Plugins](https://lsp-plug.in/) - VST Plugins Used In Carla

## Feedback

Created by **@stitoo**. Reach out on Discord or open a GitHub Issue!
