#!/usr/bin/env python3
"""
Home Assistant MQTT light integration for DFRobot Gravity GP8413 DAC.

This script connects to an MQTT broker and exposes the GP8413 as a dimmable light
in Home Assistant. Both DAC channels are controlled together as a single light.

Prerequisites:
1. Install paho-mqtt: pip install paho-mqtt
2. Enable I2C on the Raspberry Pi
3. DFRobot_GP8XXX.py should be in the same directory (included in repository)
4. Run with sudo for GPIO access
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from typing import Any, Optional

try:
    import paho.mqtt.client as mqtt
except ImportError as exc:
    raise SystemExit(
        "paho-mqtt not installed. Install with: pip install paho-mqtt"
    ) from exc

try:
    from DFRobot_GP8XXX import DFRobot_GP8413
except ImportError as exc:
    raise SystemExit(
        "Unable to import DFRobot_GP8413. Ensure DFRobot_GP8XXX.py is in the same "
        "directory as this script or add it to PYTHONPATH. "
        "The file is included in this repository."
    ) from exc


class GP8413LightController:
    """Controls GP8413 DAC as a Home Assistant light via MQTT."""

    def __init__(
        self,
        dac: DFRobot_GP8413,
        voltage_range: float,
        mqtt_client: mqtt.Client,
        base_topic: str,
        device_name: str = "GP8413 Light",
        fade_duration: float = 0.5,
    ):
        self.dac = dac
        self.voltage_range = voltage_range
        self.mqtt_client = mqtt_client
        self.base_topic = base_topic.rstrip("/")
        self.device_name = device_name
        self.fade_duration = fade_duration
        self.is_on = False
        self.brightness = 255  # 0-255
        self._current_voltage = 0.0
        self._target_voltage = 0.0
        self._fade_lock = threading.Lock()
        self._fade_stop_event = threading.Event()
        self._fade_thread: Optional[threading.Thread] = None

    def brightness_to_voltage(self, brightness: int) -> float:
        """Convert Home Assistant brightness (0-255) to voltage.
        
        Mapping:
        - 0 -> 0V (off)
        - 1-255 -> 1V to max_voltage (linear)
        - 0 < V < 1 is undefined range (not used)
        """
        if brightness == 0:
            return 0.0
        # Map 1-255 to 1V to max voltage (linear)
        # Range 0 < V < 1 is undefined and not used
        min_voltage = 1.0
        max_voltage = self.voltage_range
        # Map brightness 1-255 to voltage 1V-maxV
        ratio = (brightness - 1) / 254.0  # 1->0.0, 255->1.0
        return min_voltage + (max_voltage - min_voltage) * ratio

    def set_light_state(self, state: str, brightness: Optional[int] = None) -> None:
        """Set the light state and start fading to target voltage."""
        if state.upper() == "ON":
            self.is_on = True
            if brightness is not None:
                self.brightness = max(0, min(255, brightness))
        elif state.upper() == "OFF":
            self.is_on = False
            self.brightness = 0

        # Calculate target voltage
        if self.is_on and self.brightness > 0:
            target_voltage = self.brightness_to_voltage(self.brightness)
        else:
            target_voltage = 0.0

        # Start fade to target voltage
        self._start_fade(target_voltage)

        # Publish state update
        self._publish_state()

    def _update_dac(self, voltage: float) -> None:
        """Update the DAC output voltage."""
        # Clamp voltage to valid range (0V or 1V to max)
        if 0 < voltage < 1.0:
            # Undefined range, clamp to nearest valid value
            voltage = 0.0 if voltage < 0.5 else 1.0
        
        max_counts = DFRobot_GP8413.RESOLUTION_15_BIT
        raw_value = round((voltage / self.voltage_range) * max_counts)
        raw_value = max(0, min(raw_value, max_counts))
        self.dac.set_dac_out_voltage(raw_value, channel=2)  # channel 2 = both outputs

    def _start_fade(self, target_voltage: float) -> None:
        """Start a smooth fade to the target voltage."""
        with self._fade_lock:
            # Stop any existing fade
            self._fade_stop_event.set()
            if self._fade_thread and self._fade_thread.is_alive():
                self._fade_thread.join(timeout=0.1)
            
            # Update target
            self._target_voltage = target_voltage
            
            # Get current voltage (may be mid-fade)
            current_voltage = self._current_voltage
            
            # If already at target, no fade needed
            if abs(current_voltage - target_voltage) < 0.01:
                return
            
            # Start new fade thread
            self._fade_stop_event.clear()
            self._fade_thread = threading.Thread(
                target=self._fade_worker, daemon=True
            )
            self._fade_thread.start()

    def _fade_worker(self) -> None:
        """Worker thread that performs smooth voltage transitions."""
        with self._fade_lock:
            start_voltage = self._current_voltage
            target_voltage = self._target_voltage
        voltage_diff = target_voltage - start_voltage
        
        # Fade duration: scale based on voltage difference
        max_voltage_diff = self.voltage_range
        fade_duration = self.fade_duration * (abs(voltage_diff) / max_voltage_diff)
        fade_duration = max(0.05, min(5.0, fade_duration))  # Clamp between 0.05-5.0s
        
        # Update rate: 50Hz (20ms per step)
        update_interval = 0.02
        num_steps = int(fade_duration / update_interval)
        num_steps = max(1, num_steps)  # At least 1 step
        
        start_time = time.time()
        
        for step in range(num_steps + 1):
            if self._fade_stop_event.is_set():
                break
            
            # Calculate current voltage (linear interpolation)
            progress = step / num_steps
            current_voltage = start_voltage + voltage_diff * progress
            
            # Update DAC
            with self._fade_lock:
                self._current_voltage = current_voltage
                self._update_dac(current_voltage)
            
            # Sleep until next update
            elapsed = time.time() - start_time
            next_update_time = (step + 1) * update_interval
            sleep_time = next_update_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Ensure we end at exactly the target voltage
        with self._fade_lock:
            self._current_voltage = target_voltage
            self._update_dac(target_voltage)

    def _publish_state(self) -> None:
        """Publish current state to MQTT."""
        state_topic = f"{self.base_topic}/state"
        state = "ON" if self.is_on and self.brightness > 0 else "OFF"
        payload = state
        if self.is_on and self.brightness > 0:
            payload = f"{state}\n{self.brightness}"
        self.mqtt_client.publish(state_topic, payload, retain=True)

    def publish_discovery_config(self, unique_id: str) -> None:
        """Publish Home Assistant MQTT discovery configuration."""
        config_topic = f"homeassistant/light/{unique_id}/config"
        state_topic = f"{self.base_topic}/state"
        command_topic = f"{self.base_topic}/set"

        config = {
            "name": self.device_name,
            "unique_id": unique_id,
            "state_topic": state_topic,
            "command_topic": command_topic,
            "brightness_state_topic": state_topic,
            "brightness_command_topic": command_topic,
            "brightness_scale": 255,
            "state_value_template": "{{ value.split('\\n')[0] }}",
            "brightness_value_template": "{{ value.split('\\n')[1] }}",
            "payload_on": "ON",
            "payload_off": "OFF",
            "retain": True,
            "device": {
                "identifiers": [unique_id],
                "name": self.device_name,
                "model": "GP8413",
                "manufacturer": "DFRobot",
            },
        }

        self.mqtt_client.publish(
            config_topic, json.dumps(config), retain=True, qos=1
        )


def on_connect(client: mqtt.Client, userdata: Any, flags: dict, rc: int) -> None:
    """Callback when MQTT client connects."""
    if rc == 0:
        print("Connected to MQTT broker")
        controller = userdata["controller"]
        base_topic = userdata["base_topic"]
        # Subscribe to command topic
        command_topic = f"{base_topic}/set"
        client.subscribe(command_topic, qos=1)
        print(f"Subscribed to {command_topic}")
        # Publish discovery config
        controller.publish_discovery_config(userdata["unique_id"])
        # Publish initial state
        controller._publish_state()
    else:
        print(f"Failed to connect to MQTT broker, return code {rc}")
        sys.exit(1)


def on_message(
    client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage
) -> None:
    """Callback when MQTT message is received."""
    controller = userdata["controller"]
    payload = msg.payload.decode("utf-8").strip()

    # Check if payload is a pure number (brightness-only command from slider)
    try:
        brightness_value = int(payload)
        # This is a brightness-only command
        if brightness_value == 0:
            # Brightness 0 means turn OFF
            controller.set_light_state("OFF", 0)
            print(f"Light set: OFF, brightness: 0")
        else:
            # Brightness > 0: turn ON if currently OFF, otherwise keep current state
            if not controller.is_on:
                controller.set_light_state("ON", brightness_value)
                print(f"Light set: ON, brightness: {brightness_value}")
            else:
                # Light is already ON, just update brightness
                controller.set_light_state("ON", brightness_value)
                print(f"Light set: ON, brightness: {brightness_value}")
        return
    except ValueError:
        # Not a pure number, continue with normal parsing
        pass

    # Parse Home Assistant light command
    # Format can be: "ON", "OFF", or "ON\n255" (state\nbrightness)
    lines = payload.split("\n")
    state = lines[0].upper()
    brightness = None

    if len(lines) > 1:
        try:
            brightness = int(lines[1])
        except ValueError:
            pass

    # If brightness not provided, use current brightness for ON, 0 for OFF
    if brightness is None:
        if state == "ON":
            brightness = controller.brightness if controller.brightness > 0 else 255
        else:
            brightness = 0

    controller.set_light_state(state, brightness)
    print(f"Light set: {state}, brightness: {brightness}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Home Assistant MQTT light integration for GP8413 DAC."
    )
    parser.add_argument(
        "--mqtt-host",
        default="localhost",
        help="MQTT broker hostname (default: localhost)",
    )
    parser.add_argument(
        "--mqtt-port", type=int, default=1883, help="MQTT broker port (default: 1883)"
    )
    parser.add_argument(
        "--mqtt-username",
        help="MQTT broker username (optional)",
    )
    parser.add_argument(
        "--mqtt-password",
        help="MQTT broker password (optional)",
    )
    parser.add_argument(
        "--mqtt-topic",
        default="homeassistant/light/gp8413",
        help="MQTT base topic (default: homeassistant/light/gp8413)",
    )
    parser.add_argument(
        "--device-name",
        default="GP8413 Light",
        help="Device name in Home Assistant (default: GP8413 Light)",
    )
    parser.add_argument(
        "--unique-id",
        default="gp8413_light",
        help="Unique ID for Home Assistant (default: gp8413_light)",
    )
    parser.add_argument(
        "--range",
        choices=("0-5V", "0-10V"),
        default="0-10V",
        help="DAC output voltage range (default: 0-10V)",
    )
    parser.add_argument(
        "--sda-pin",
        type=int,
        default=2,
        help="BCM pin number for SDA (default: 2)",
    )
    parser.add_argument(
        "--scl-pin",
        type=int,
        default=3,
        help="BCM pin number for SCL (default: 3)",
    )
    parser.add_argument(
        "--address",
        type=lambda value: int(value, 0),
        default=0x58,
        help="I2C address of the GP8413 (default: 0x58)",
    )
    parser.add_argument(
        "--fade-duration",
        type=float,
        default=0.5,
        help="Fade duration in seconds for full range transitions (default: 0.5)",
    )

    args = parser.parse_args()

    # Initialize DAC
    range_code = (
        DFRobot_GP8413.OUTPUT_RANGE_5V if args.range == "0-5V" else DFRobot_GP8413.OUTPUT_RANGE_10V
    )
    voltage_range = 5.0 if args.range == "0-5V" else 10.0

    dac = DFRobot_GP8413(
        i2c_sda=args.sda_pin,
        i2c_scl=args.scl_pin,
        i2c_addr=args.address,
    )

    if dac.begin() != 0:
        raise SystemExit(
            "Failed to initialize the GP8413. "
            "Double-check wiring, power, and the selected I2C address."
        )

    dac.set_dac_outrange(range_code)
    print(f"GP8413 initialized with {args.range} range")

    # Initialize MQTT client
    client = mqtt.Client(client_id=f"gp8413_{args.unique_id}")
    if args.mqtt_username:
        client.username_pw_set(args.mqtt_username, args.mqtt_password)

    # Initialize controller
    controller = GP8413LightController(
        dac=dac,
        voltage_range=voltage_range,
        mqtt_client=client,
        base_topic=args.mqtt_topic,
        device_name=args.device_name,
        fade_duration=args.fade_duration,
    )

    # Set up MQTT callbacks
    userdata = {
        "controller": controller,
        "base_topic": args.mqtt_topic,
        "unique_id": args.unique_id,
    }
    client.user_data_set(userdata)
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to MQTT broker
    print(f"Connecting to MQTT broker at {args.mqtt_host}:{args.mqtt_port}...")
    try:
        client.connect(args.mqtt_host, args.mqtt_port, 60)
    except Exception as e:
        raise SystemExit(f"Failed to connect to MQTT broker: {e}")

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down...")
        # Stop any ongoing fade
        controller._fade_stop_event.set()
        if controller._fade_thread and controller._fade_thread.is_alive():
            controller._fade_thread.join(timeout=0.5)
        # Turn off light
        controller.set_light_state("OFF")
        # Wait a moment for fade to complete
        time.sleep(0.1)
        client.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start MQTT loop
    print("Running MQTT light controller. Press Ctrl+C to stop.")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()

