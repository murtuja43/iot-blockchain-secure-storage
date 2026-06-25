"""End-to-end integration tests across all layers:
simulator -> API -> blockchain -> storage -> reload -> validation."""

import json

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.blockchain.validation import validate_chain
from app.config import API_PREFIX
from app.storage.json_store import JsonBlockchainStore
from simulator.client import BlockchainAPIClient
from simulator.run_simulator import build_devices, register_all


def _run_pipeline(store: JsonBlockchainStore) -> None:
    """Drive the real simulator against the real API backed by ``store``."""
    app = create_app(store=store, difficulty=2)
    with TestClient(app) as tc:
        client = BlockchainAPIClient(base_url="", session=tc)
        devices = register_all(build_devices(client))
        assert len(devices) == 3
        for device in devices:
            device.send_once()
    # On context exit the chain has been persisted (saved on every telemetry).


def test_simulator_to_api_to_blockchain_to_storage(tmp_path):
    path = tmp_path / "chain.json"
    store = JsonBlockchainStore(path)
    _run_pipeline(store)

    # The signed readings travelled all the way to disk.
    assert path.is_file()
    reloaded = store.load()
    assert len(reloaded) == 4  # genesis + 3 device readings
    device_ids = {
        tx["device_id"] for block in reloaded.blocks for tx in block.transactions
    }
    assert device_ids == {"temperature-001", "humidity-001", "pressure-001"}


def test_storage_reload_then_validation(tmp_path):
    path = tmp_path / "chain.json"
    _run_pipeline(JsonBlockchainStore(path))

    # Simulate a restart: a brand-new store loads the same file and validates.
    fresh_store = JsonBlockchainStore(path)
    assert validate_chain(fresh_store.load()).is_valid is True

    # ...and the API, restarted on that store, agrees.
    app = create_app(store=fresh_store, difficulty=2)
    with TestClient(app) as tc:
        assert tc.get(f"{API_PREFIX}/chain").json()["length"] == 4
        assert tc.get(f"{API_PREFIX}/validate").json()["valid"] is True


def test_tampered_chain_is_detected_after_reload(tmp_path):
    path = tmp_path / "chain.json"
    _run_pipeline(JsonBlockchainStore(path))

    # Attacker edits a stored telemetry value directly in the file.
    data = json.loads(path.read_text())
    data["blocks"][1]["transactions"][0]["payload"]["value"] = 12345.0
    path.write_text(json.dumps(data))

    # Reload + validate -> detected, with the offending block identified.
    result = validate_chain(JsonBlockchainStore(path).load())
    assert result.is_valid is False
    assert result.block_index == 1

    # The API's /validate endpoint reports it too.
    app = create_app(store=JsonBlockchainStore(path), difficulty=2)
    with TestClient(app) as tc:
        assert tc.get(f"{API_PREFIX}/validate").json()["valid"] is False
