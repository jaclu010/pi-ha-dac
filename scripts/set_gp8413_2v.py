#!/usr/bin/env python3
"""
Drive a DFRobot Gravity GP8413 dual-channel DAC and set both outputs to 2 V.

Prerequisites:
1. Enable I2C on the Raspberry Pi and wire SDA/SCL to BCM pins 2/3 (or update
   the --sda-pin/--scl-pin flags).
2. DFRobot_GP8XXX.py should be in the same directory (included in repository).
3. Run the script with sudo so RPi.GPIO can toggle the pins.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Tuple

try:
    from DFRobot_GP8XXX import DFRobot_GP8413
except ImportError as exc:  # pragma: no cover - hardware import guard
    raise SystemExit(
        "Unable to import DFRobot_GP8413. Ensure DFRobot_GP8XXX.py is in the same "
        "directory as this script or add it to PYTHONPATH. "
        "The file is included in this repository."
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set both GP8413 output channels to the requested voltage."
    )
    parser.add_argument(
        "--voltage",
        type=float,
        default=2.0,
        help="Target output voltage (default: 2.0 V).",
    )
    parser.add_argument(
        "--range",
        choices=("0-5V", "0-10V"),
        default="0-10V",
        help="Configured GP8413 range (default: 0-10V).",
    )
    parser.add_argument(
        "--sda-pin",
        type=int,
        default=2,
        help="BCM pin number for SDA (default: 2).",
    )
    parser.add_argument(
        "--scl-pin",
        type=int,
        default=3,
        help="BCM pin number for SCL (default: 3).",
    )
    parser.add_argument(
        "--address",
        type=lambda value: int(value, 0),
        default=0x58,
        help="I2C address of the GP8413 (default: 0x58).",
    )
    parser.add_argument(
        "--store",
        action="store_true",
        help="Persist the voltage to the chip's flash (optional).",
    )
    return parser.parse_args()


def range_settings(range_arg: str) -> Tuple[int, float]:
    if range_arg == "0-5V":
        return DFRobot_GP8413.OUTPUT_RANGE_5V, 5.0
    return DFRobot_GP8413.OUTPUT_RANGE_10V, 10.0


def main() -> None:
    args = parse_args()
    range_code, span = range_settings(args.range)

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

    target_voltage = max(0.0, min(args.voltage, span))
    max_counts = DFRobot_GP8413.RESOLUTION_15_BIT
    raw_value = round((target_voltage / span) * max_counts)
    raw_value = max(0, min(raw_value, max_counts))

    dac.set_dac_out_voltage(raw_value, channel=2)  # channel 2 = both outputs

    if args.store:
        # Give the chip a moment before issuing the store command.
        time.sleep(0.05)
        dac.store()

    print(
        f"GP8413 output range {args.range}: "
        f"set both channels to {target_voltage:.3f} V (raw={raw_value})."
    )


if __name__ == "__main__":
    main()

