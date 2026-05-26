"""
IoT Simulator CLI
=================
Run a background simulation that generates realistic barcode scanner
and RFID reader events against the live API.

Usage:
    python scripts/iot_simulator.py
    python scripts/iot_simulator.py --interval 0.5 --error-rate 0.1
    python scripts/iot_simulator.py --timeout 30

The simulator uses 8 virtual devices and cycles through scan events,
tag reads, heartbeats, and occasional errors.
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from iot.simulator import IoTSimulator


def main():
    parser = argparse.ArgumentParser(description="IoT Event Simulator")
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="Interval range midpoint (seconds) between events (default: 1.0)",
    )
    parser.add_argument(
        "--error-rate", type=float, default=0.05,
        help="Probability of generating an error event (0-1, default: 0.05)",
    )
    parser.add_argument(
        "--timeout", type=int, default=0,
        help="Stop after N seconds (default: run until Ctrl+C)",
    )
    args = parser.parse_args()

    sim = IoTSimulator(interval_range=(args.interval * 0.5, args.interval * 1.5), error_rate=args.error_rate)

    try:
        sim.start()
        print(f"*** IoT Simulator Running ***")
        print(f"  8 virtual devices sending events every ~{args.interval}s")
        print(f"  Error rate: {args.error_rate * 100:.0f}%")
        print(f"  Press Ctrl+C to stop")

        if args.timeout > 0:
            print(f"  Will auto-stop after {args.timeout}s")
            time.sleep(args.timeout)
            sim.stop()
            print("*** Timed out - stopped ***")
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        sim.stop()
        print("*** Stopped by user ***")


if __name__ == "__main__":
    main()
