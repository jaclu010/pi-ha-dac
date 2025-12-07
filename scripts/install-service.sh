#!/bin/bash
# Installation script for GP8413 Home Assistant service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="gp8413-homeassistant"
INSTALL_DIR="/opt/gp8413"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
CONFIG_FILE="/etc/gp8413/config"

echo "Installing GP8413 Home Assistant service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Create installation directory
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Copy script files
echo "Copying script files..."
cp "$SCRIPT_DIR/gp8413_homeassistant.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/gp8413-service-wrapper.sh" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/DFRobot_GP8XXX.py" "$INSTALL_DIR/"

# Make scripts executable
chmod +x "$INSTALL_DIR/gp8413_homeassistant.py"
chmod +x "$INSTALL_DIR/gp8413-service-wrapper.sh"

# Create config directory and file if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating configuration file: $CONFIG_FILE"
    mkdir -p "$(dirname "$CONFIG_FILE")"
    cp "$SCRIPT_DIR/gp8413-config.env.example" "$CONFIG_FILE"
    echo ""
    echo "IMPORTANT: Please edit $CONFIG_FILE and update with your MQTT credentials and settings"
    echo "  sudo nano $CONFIG_FILE"
else
    echo "Configuration file already exists: $CONFIG_FILE"
fi

# Install systemd service
echo "Installing systemd service..."
cp "$SCRIPT_DIR/gp8413-homeassistant.service.template" "$SERVICE_FILE"

# Reload systemd
systemctl daemon-reload

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit the configuration file: sudo nano $CONFIG_FILE"
echo "2. Enable and start the service:"
echo "   sudo systemctl enable $SERVICE_NAME"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo "Check service status: sudo systemctl status $SERVICE_NAME"
echo "View logs: sudo journalctl -u $SERVICE_NAME -f"

