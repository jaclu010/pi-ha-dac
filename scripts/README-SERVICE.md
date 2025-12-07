# GP8413 Home Assistant Service Installation

This guide explains how to install the GP8413 Home Assistant integration as a systemd service that runs automatically on boot.

## Prerequisites

- Raspberry Pi (or Linux system with systemd)
- Python 3 installed
- paho-mqtt library: `pip3 install paho-mqtt`
- DFRobot_GP8XXX.py driver file
- MQTT broker running (e.g., Mosquitto)

## Quick Installation

1. **Run the installation script:**
   ```bash
   sudo ./scripts/install-service.sh
   ```

2. **Edit the configuration file:**
   ```bash
   sudo nano /etc/gp8413/config
   ```
   Update with your MQTT credentials and settings.

3. **Ensure DFRobot_GP8XXX.py is in place:**
   ```bash
   sudo cp DFRobot_GP8XXX.py /opt/gp8413/
   ```

4. **Enable and start the service:**
   ```bash
   sudo systemctl enable gp8413-homeassistant
   sudo systemctl start gp8413-homeassistant
   ```

## Manual Installation

If you prefer to install manually:

1. **Create installation directory:**
   ```bash
   sudo mkdir -p /opt/gp8413
   ```

2. **Copy files:**
   ```bash
   sudo cp scripts/gp8413_homeassistant.py /opt/gp8413/
   sudo cp scripts/gp8413-service-wrapper.sh /opt/gp8413/
   sudo cp DFRobot_GP8XXX.py /opt/gp8413/
   sudo chmod +x /opt/gp8413/gp8413_homeassistant.py
   sudo chmod +x /opt/gp8413/gp8413-service-wrapper.sh
   ```

3. **Create configuration file:**
   ```bash
   sudo mkdir -p /etc/gp8413
   sudo cp scripts/gp8413-config.env.example /etc/gp8413/config
   sudo nano /etc/gp8413/config
   ```
   Update with your settings.

4. **Install systemd service:**
   ```bash
   sudo cp scripts/gp8413-homeassistant.service.template /etc/systemd/system/gp8413-homeassistant.service
   sudo systemctl daemon-reload
   ```

5. **Enable and start:**
   ```bash
   sudo systemctl enable gp8413-homeassistant
   sudo systemctl start gp8413-homeassistant
   ```

## Service Management

**Check status:**
```bash
sudo systemctl status gp8413-homeassistant
```

**View logs:**
```bash
sudo journalctl -u gp8413-homeassistant -f
```

**Stop service:**
```bash
sudo systemctl stop gp8413-homeassistant
```

**Start service:**
```bash
sudo systemctl start gp8413-homeassistant
```

**Restart service:**
```bash
sudo systemctl restart gp8413-homeassistant
```

**Disable auto-start:**
```bash
sudo systemctl disable gp8413-homeassistant
```

## Configuration

The service reads configuration from `/etc/gp8413/config`. Available settings:

- `MQTT_HOST` - MQTT broker hostname (default: localhost)
- `MQTT_PORT` - MQTT broker port (default: 1883)
- `MQTT_USERNAME` - MQTT username (optional)
- `MQTT_PASSWORD` - MQTT password (optional)
- `MQTT_TOPIC` - MQTT base topic (default: homeassistant/light/gp8413)
- `DEVICE_NAME` - Device name in Home Assistant
- `UNIQUE_ID` - Unique identifier for the device
- `VOLTAGE_RANGE` - DAC range: 0-5V or 0-10V (default: 0-10V)
- `SDA_PIN` - BCM pin for SDA (default: 2)
- `SCL_PIN` - BCM pin for SCL (default: 3)
- `I2C_ADDRESS` - I2C address (default: 0x58)
- `FADE_DURATION` - Fade duration in seconds (default: 0.5)

After changing the configuration file, restart the service:
```bash
sudo systemctl restart gp8413-homeassistant
```

## Troubleshooting

**Service won't start:**
- Check logs: `sudo journalctl -u gp8413-homeassistant -n 50`
- Verify DFRobot_GP8XXX.py is in `/opt/gp8413/`
- Check I2C is enabled: `sudo raspi-config` → Interface Options → I2C
- Verify MQTT broker is running: `sudo systemctl status mosquitto`

**Permission errors:**
- Service runs as root (required for GPIO access)
- Ensure script is executable: `sudo chmod +x /opt/gp8413/gp8413_homeassistant.py`

**MQTT connection issues:**
- Verify MQTT broker is accessible
- Check credentials in `/etc/gp8413/config`
- Test MQTT connection manually: `mosquitto_pub -h localhost -t test -m "hello"`

## Uninstallation

To remove the service:

```bash
sudo systemctl stop gp8413-homeassistant
sudo systemctl disable gp8413-homeassistant
sudo rm /etc/systemd/system/gp8413-homeassistant.service
sudo systemctl daemon-reload
sudo rm -rf /opt/gp8413
sudo rm -rf /etc/gp8413
```

