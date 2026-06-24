"""Run the IoT simulator: 3+ devices streaming signed telemetry concurrently.

Each device runs in its own thread, sending a reading every ``--interval``
seconds. A shared ``threading.Event`` provides graceful shutdown: on Ctrl+C (or
after an optional ``--duration``) the event is set, every device loop exits at
its next check, and the threads are joined cleanly.

Run from the project root:
    PYTHONPATH=src python -m simulator.run_simulator --interval 5
or simply:
    python simulator/run_simulator.py --interval 5
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `app` (under src/) and `simulator` (repo root) importable whether this is
# run as a module or as a plain script. Idempotent: skips paths already present.
_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import argparse  # noqa: E402
import threading  # noqa: E402

from app.config import API_BASE_URL, TELEMETRY_INTERVAL_SECONDS  # noqa: E402
from simulator.client import APIError, BlockchainAPIClient  # noqa: E402
from simulator.device import SimulatedDevice  # noqa: E402
from simulator.generators import (  # noqa: E402
    humidity_generator,
    pressure_generator,
    temperature_generator,
)


def build_devices(client: BlockchainAPIClient) -> list[SimulatedDevice]:
    """Create the three standard sensors."""
    return [
        SimulatedDevice("temperature-001", temperature_generator(), client),
        SimulatedDevice("humidity-001", humidity_generator(), client),
        SimulatedDevice("pressure-001", pressure_generator(), client),
    ]


def register_all(devices: list[SimulatedDevice]) -> list[SimulatedDevice]:
    """Register each device; return only those that registered successfully."""
    ready = []
    for device in devices:
        try:
            device.register()
            print(f"[register] {device.device_id}: ok", flush=True)
            ready.append(device)
        except APIError as e:
            print(f"[register] {device.device_id}: FAILED ({e})", flush=True)
    return ready


def run_device_loop(
    device: SimulatedDevice, interval: float, stop_event: threading.Event
) -> None:
    """Send telemetry every ``interval`` seconds until ``stop_event`` is set."""
    while not stop_event.is_set():
        try:
            reading = device.create_telemetry()
            result = device.client.send_telemetry(reading)
            value = reading["payload"]["value"]
            unit = reading["payload"]["unit"]
            print(
                f"[{device.device_id}] {value} {unit} "
                f"-> block {result['block_index']} (chain length {result['chain_length']})",
                flush=True,
            )
        except APIError as e:
            print(f"[{device.device_id}] send failed: {e}", flush=True)
        stop_event.wait(interval)  # responsive sleep (wakes instantly on stop)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IoT blockchain telemetry simulator")
    parser.add_argument(
        "--interval", type=float, default=TELEMETRY_INTERVAL_SECONDS,
        help="seconds between readings per device",
    )
    parser.add_argument(
        "--url", default=API_BASE_URL, help="base URL of the blockchain API",
    )
    parser.add_argument(
        "--duration", type=float, default=0.0,
        help="auto-stop after N seconds (0 = run until Ctrl+C)",
    )
    args = parser.parse_args(argv)

    print(f"Starting simulator -> {args.url} (interval={args.interval}s)", flush=True)
    client = BlockchainAPIClient(base_url=args.url)
    devices = register_all(build_devices(client))
    if not devices:
        print("No devices registered; is the API running? Exiting.", flush=True)
        return 1

    stop_event = threading.Event()
    threads = [
        threading.Thread(
            target=run_device_loop, args=(d, args.interval, stop_event), daemon=True
        )
        for d in devices
    ]
    for t in threads:
        t.start()

    try:
        if args.duration > 0:
            stop_event.wait(args.duration)
        else:
            while not stop_event.is_set():
                stop_event.wait(0.5)
    except KeyboardInterrupt:
        print("\nCtrl+C received - shutting down...", flush=True)
    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=args.interval + 2)
        print("All devices stopped. Goodbye.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
