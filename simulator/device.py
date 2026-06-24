"""A simulated IoT sensor device.

Each device owns an ECDSA key pair (generated on creation), registers its PUBLIC
key with the server, and then repeatedly: produces a reading, signs it with its
PRIVATE key, and sends it. The signing reuses the SAME canonical contract the
server verifies against (``telemetry_signable_dict`` + ``serialize``), so the
device and server can never disagree about what bytes were signed.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from app.api.schemas import telemetry_signable_dict
from app.crypto.serialization import serialize
from app.crypto.signatures import generate_key_pair, sign
from simulator.client import APIError, BlockchainAPIClient
from simulator.generators import SensorGenerator


class SimulatedDevice:
    """One sensor: holds a key pair, signs readings, and sends them via the API."""

    def __init__(
        self,
        device_id: str,
        generator: SensorGenerator,
        client: BlockchainAPIClient,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.device_id = device_id
        self.generator = generator
        self.client = client
        self.clock = clock
        # Generate the device's ECDSA key pair automatically.
        self.private_key_pem, self.public_key_pem = generate_key_pair()
        self.registered = False

    def register(self) -> bool:
        """Register this device's public key with the server.

        A 409 (already registered, e.g. on a re-run) is treated as success so
        the simulator is safe to restart.
        """
        try:
            self.client.register_device(self.device_id, self.public_key_pem)
        except APIError as e:
            if e.status_code == 409:
                self.registered = True
                return True
            raise
        self.registered = True
        return True

    def create_telemetry(self) -> dict[str, Any]:
        """Build a signed telemetry packet (device_id, timestamp, payload, signature)."""
        timestamp = self.clock()
        payload = self.generator.next_reading()
        signature = sign(
            self.private_key_pem,
            serialize(telemetry_signable_dict(self.device_id, timestamp, payload)),
        )
        return {
            "device_id": self.device_id,
            "timestamp": timestamp,
            "payload": payload,
            "signature": signature,
        }

    def send_once(self) -> dict[str, Any]:
        """Create one reading and submit it; returns the API's response body."""
        return self.client.send_telemetry(self.create_telemetry())
