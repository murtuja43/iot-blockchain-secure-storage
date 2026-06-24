"""Simulator workflow tests: device assembly, registration, and a full
end-to-end run against the real API (driven through FastAPI's TestClient)."""

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import API_PREFIX
from app.storage.json_store import JsonBlockchainStore
from simulator.client import APIError, BlockchainAPIClient
from simulator.device import SimulatedDevice
from simulator.run_simulator import build_devices, register_all


class _PickyClient:
    """Fake client that refuses to register the humidity sensor."""

    def __init__(self):
        self.registered = []

    def register_device(self, device_id, public_key_pem):
        if device_id == "humidity-001":
            raise APIError(400, "rejected")
        self.registered.append(device_id)
        return {"device_id": device_id}


def test_build_devices_creates_three_named_sensors():
    devices = build_devices(client=_PickyClient())
    ids = [d.device_id for d in devices]
    assert ids == ["temperature-001", "humidity-001", "pressure-001"]
    assert all(isinstance(d, SimulatedDevice) for d in devices)


def test_register_all_skips_failed_registrations():
    devices = build_devices(client=_PickyClient())
    ready = register_all(devices)
    ready_ids = [d.device_id for d in ready]
    assert "humidity-001" not in ready_ids
    assert ready_ids == ["temperature-001", "pressure-001"]


def test_end_to_end_simulator_against_real_api(tmp_path):
    """Three devices register and stream signed telemetry into the real chain."""
    store = JsonBlockchainStore(tmp_path / "chain.json")  # isolated temp store
    app = create_app(store=store, difficulty=2)
    with TestClient(app) as tc:
        # Point the simulator's client at the in-process test server.
        client = BlockchainAPIClient(base_url="", session=tc)

        devices = register_all(build_devices(client))
        assert len(devices) == 3

        for device in devices:
            response = device.send_once()
            assert response["message"] == "telemetry accepted"

        # The chain now holds genesis + one block per device.
        assert client.get_chain()["length"] == 4

        # The whole chain validates (every signature + hash + link checks out).
        assert tc.get(f"{API_PREFIX}/validate").json()["valid"] is True

        # Per-device history works for a real, signed reading.
        history = tc.get(f"{API_PREFIX}/device/temperature-001").json()
        assert history["total_records"] == 1
        assert history["records"][0]["device_id"] == "temperature-001"
