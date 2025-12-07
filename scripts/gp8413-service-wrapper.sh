#!/bin/bash
# Wrapper script for GP8413 Home Assistant service
# Reads configuration from /etc/gp8413/config and runs the Python script

# Load configuration file if it exists
if [ -f /etc/gp8413/config ]; then
    set -a
    source /etc/gp8413/config
    set +a
fi

# Set defaults if not provided
MQTT_HOST=${MQTT_HOST:-localhost}
MQTT_PORT=${MQTT_PORT:-1883}
MQTT_USERNAME=${MQTT_USERNAME:-}
MQTT_PASSWORD=${MQTT_PASSWORD:-}
MQTT_TOPIC=${MQTT_TOPIC:-homeassistant/light/gp8413}
DEVICE_NAME=${DEVICE_NAME:-GP8413 Light}
UNIQUE_ID=${UNIQUE_ID:-gp8413_light}
VOLTAGE_RANGE=${VOLTAGE_RANGE:-0-10V}
SDA_PIN=${SDA_PIN:-2}
SCL_PIN=${SCL_PIN:-3}
I2C_ADDRESS=${I2C_ADDRESS:-0x58}
FADE_DURATION=${FADE_DURATION:-0.5}

# Build command arguments
ARGS=(
    --mqtt-host "$MQTT_HOST"
    --mqtt-port "$MQTT_PORT"
    --mqtt-topic "$MQTT_TOPIC"
    --device-name "$DEVICE_NAME"
    --unique-id "$UNIQUE_ID"
    --range "$VOLTAGE_RANGE"
    --sda-pin "$SDA_PIN"
    --scl-pin "$SCL_PIN"
    --address "$I2C_ADDRESS"
    --fade-duration "$FADE_DURATION"
)

# Add optional MQTT credentials if provided
if [ -n "$MQTT_USERNAME" ]; then
    ARGS+=(--mqtt-username "$MQTT_USERNAME")
fi

if [ -n "$MQTT_PASSWORD" ]; then
    ARGS+=(--mqtt-password "$MQTT_PASSWORD")
fi

# Execute the Python script
exec /usr/bin/python3 /opt/gp8413/gp8413_homeassistant.py "${ARGS[@]}"

