"""Unit tests for the SimulatedDevice (signing + registration + sending)."""

import pytest

from app.api.schemas import telemetry_signable_dict
from app.crypto.serialization import serialize
from app.crypto.signatures import verify
from simulator.client import APIError
from simulator.device import SimulatedDevice
from simulator.generators import temperature_generator


class FakeClient:
    """Records calls instead of making real HTTP requests."""

    def __init__(self, register_error: APIError | None = None):
        self.registered: dict[str, str] = {}
        self.telemetry: list[dict] = []
        self.register_error = register_error

    def register_device(self, device_id, public_key_pem):
        if self.register_error is not None:
            raise self.register_error
        self.registered[device_id] = public_key_pem
        return {"device_id": device_id, "message": "ok"}

    def send_telemetry(self, transaction):
        self.telemetry.append(transaction)
        return {
            "message": "ok",
            "block_index": len(self.telemetry),
            "block_hash": "00abc",
            "chain_length": len(self.telemetry) + 1,
        }


def make_device(client=None, device_id="temp-01"):
    return SimulatedDevice(device_id, temperature_generator(), client or FakeClient())


def test_device_generates_keypair_on_creation():
    device = make_device()
    assert "PRIVATE KEY" in device.private_key_pem
    assert "PUBLIC KEY" in device.public_key_pem


def test_create_telemetry_structure():
    device = make_device()
    tel = device.create_telemetry()
    assert set(tel) == {"device_id", "timestamp", "payload", "signature"}
    assert set(tel["payload"]) == {"value", "unit"}


def test_created_telemetry_signature_is_valid():
    device = make_device()
    tel = device.create_telemetry()
    signable = serialize(
        telemetry_signable_dict(tel["device_id"], tel["timestamp"], tel["payload"])
    )
    # The signature must verify against the device's OWN public key.
    assert verify(device.public_key_pem, signable, tel["signature"]) is True


def test_register_calls_client_and_sets_flag():
    client = FakeClient()
    device = make_device(client, "temp-01")
    assert device.register() is True
    assert device.registered is True
    assert client.registered["temp-01"] == device.public_key_pem


def test_register_treats_409_as_already_registered():
    client = FakeClient(register_error=APIError(409, "already registered"))
    device = make_device(client)
    assert device.register() is True
    assert device.registered is True


def test_register_reraises_other_errors():
    client = FakeClient(register_error=APIError(400, "bad key"))
    device = make_device(client)
    with pytest.raises(APIError):
        device.register()


def test_send_once_submits_created_telemetry():
    client = FakeClient()
    device = make_device(client, "temp-01")
    result = device.send_once()
    assert result["block_index"] == 1
    assert len(client.telemetry) == 1
    assert client.telemetry[0]["device_id"] == "temp-01"
