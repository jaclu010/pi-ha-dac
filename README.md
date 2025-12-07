# GP8413 Home Assistant Integration

This project provides a Home Assistant MQTT integration for the DFRobot Gravity GP8413 dual-channel DAC module, allowing it to be controlled as a dimmable light from Home Assistant.

## Project Overview

The GP8413 is a 15-bit I2C DAC that can output 0-5V or 0-10V on two channels. This integration:
- Exposes both DAC channels as a single dimmable light in Home Assistant
- Maps Home Assistant brightness (0-255) to voltage (0V for off, 1-10V for 1-255)
- Provides smooth fading between brightness levels
- Runs as a systemd service for automatic startup

## Project Structure

```
.
├── scripts/
│   ├── gp8413_homeassistant.py      # Main Home Assistant integration script
│   ├── set_gp8413_2v.py             # Simple script to set both channels to 2V
│   ├── gp8413-homeassistant.service.template  # Systemd service template
│   ├── gp8413-service-wrapper.sh    # Service wrapper script
│   ├── gp8413-config.env.example    # Configuration template
│   ├── install-service.sh           # Installation script
│   └── README-SERVICE.md            # Service installation documentation
├── README.md                        # This file
└── .gitignore                        # Git ignore rules
```

## Hardware Requirements

- Raspberry Pi (or Linux system with GPIO/I2C support)
- DFRobot Gravity GP8413 DAC module
- I2C connection (SDA/SCL pins, default: BCM pins 2/3)
- MQTT broker (e.g., Mosquitto)

## Software Dependencies

- Python 3
- paho-mqtt: `pip3 install paho-mqtt`
- RPi.GPIO (for Raspberry Pi GPIO access)
- DFRobot_GP8XXX.py driver (from DFRobot GitHub repository)

## Key Components

### Main Script: `scripts/gp8413_homeassistant.py`

The main integration script that:
- Connects to MQTT broker
- Publishes Home Assistant MQTT discovery configuration
- Subscribes to light commands (ON/OFF, brightness)
- Maps brightness values to voltage (0→0V, 1-255→1-10V)
- Implements smooth fading between brightness levels
- Controls both DAC channels simultaneously

**Key Functions:**
- `brightness_to_voltage()`: Maps HA brightness (0-255) to voltage (0V or 1-10V)
- `set_light_state()`: Handles ON/OFF and brightness commands
- `_fade_worker()`: Background thread for smooth voltage transitions
- `on_message()`: MQTT message handler (supports numeric brightness commands)

### Service Installation

The project includes a complete systemd service setup:
- Service file with auto-restart and logging
- Configuration file for easy customization
- Installation script for automated setup
- Wrapper script for environment variable handling

## Voltage Mapping

The integration uses a specific voltage mapping:
- **0 (OFF)**: 0V
- **1-255**: 1V to 10V (linear mapping)
- **0 < V < 1**: Undefined range (not used, clamped to 0V or 1V)

This ensures the light is fully off at 0 and has a minimum visible output at brightness 1.

## MQTT Topics

- **Command Topic**: `homeassistant/light/gp8413/set`
- **State Topic**: `homeassistant/light/gp8413/state`
- **Discovery Config**: `homeassistant/light/gp8413_light/config`

## Usage

### Quick Test

```bash
sudo python3 scripts/gp8413_homeassistant.py \
  --mqtt-host localhost \
  --mqtt-port 1883 \
  --device-name "My GP8413 Light"
```

### Install as Service

```bash
sudo ./scripts/install-service.sh
sudo nano /etc/gp8413/config  # Edit configuration
sudo systemctl enable gp8413-homeassistant
sudo systemctl start gp8413-homeassistant
```

See `scripts/README-SERVICE.md` for detailed service installation instructions.

## Configuration

Configuration is managed via `/etc/gp8413/config` (when running as service) or command-line arguments:

- `--mqtt-host`: MQTT broker hostname
- `--mqtt-port`: MQTT broker port
- `--mqtt-username`: MQTT username (optional)
- `--mqtt-password`: MQTT password (optional)
- `--mqtt-topic`: MQTT base topic
- `--device-name`: Device name in Home Assistant
- `--unique-id`: Unique identifier
- `--range`: Voltage range (0-5V or 0-10V)
- `--sda-pin`: BCM pin for SDA (default: 2)
- `--scl-pin`: BCM pin for SCL (default: 3)
- `--address`: I2C address (default: 0x58)
- `--fade-duration`: Fade duration in seconds (default: 0.5)

## Development Notes

### Message Format Handling

The script handles multiple MQTT message formats:
- `"ON"` or `"OFF"`: State-only commands
- `"ON\n255"`: State with brightness
- `"8"`, `"115"`, etc.: Brightness-only commands (from slider)

The `on_message()` function detects numeric-only payloads and treats them as brightness commands, preserving the current ON/OFF state.

### Fading Implementation

Fading is implemented using a background thread (`_fade_worker`) that:
- Interpolates voltage values over time
- Updates at 50Hz (20ms intervals)
- Scales fade duration based on voltage difference
- Can be interrupted by new commands (stops current fade, starts new one)

### Thread Safety

The controller uses threading locks to prevent race conditions when:
- Starting new fades while a fade is in progress
- Reading/writing current voltage state
- Updating DAC values

## Troubleshooting

**Service won't start:**
- Check logs: `sudo journalctl -u gp8413-homeassistant -n 50`
- Verify DFRobot_GP8XXX.py is in `/opt/gp8413/`
- Ensure I2C is enabled: `sudo raspi-config`
- Check MQTT broker is running

**Brightness slider not working:**
- Verify the script handles numeric-only payloads (fixed in current version)
- Check MQTT message format in logs

**Permission errors:**
- Service must run as root for GPIO access
- Ensure script is executable

## Related Files

- **DFRobot Driver**: https://github.com/DFRobot/DFRobot_GP8XXX/blob/master/python/raspberryPi/DFRobot_GP8XXX.py
- **GP8413 Documentation**: https://wiki.dfrobot.com/SKU_DFR1073_2_Channel_15bit_I2C_to_0-10V_DAC

## License

This project is provided as-is for use with DFRobot GP8413 hardware.

