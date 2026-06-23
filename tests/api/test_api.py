"""Endpoint tests for the REST API + device registry."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.api.schemas import telemetry_signable_dict
from app.config import API_PREFIX
from app.crypto.serialization import serialize
from app.crypto.signatures import generate_key_pair, sign
from app.storage.json_store import JsonBlockchainStore


@pytest.fixture
def client(tmp_path):
    """A TestClient backed by a temp-file store and low PoW difficulty."""
    store = JsonBlockchainStore(tmp_path / "chain.json")
    app = create_app(store=store, difficulty=2)
    with TestClient(app) as c:  # `with` runs the lifespan startup
        yield c


# --- helpers --------------------------------------------------------------

def register_device(client, device_id="dev-1"):
    """Register a fresh device, returning its private key PEM for signing."""
    private_pem, public_pem = generate_key_pair()
    resp = client.post(
        f"{API_PREFIX}/devices/register",
        json={"device_id": device_id, "public_key": public_pem},
    )
    assert resp.status_code == 201
    return private_pem


def signed_telemetry(device_id, private_pem, value=21.5, unit="C", timestamp=1000.0):
    payload = {"value": value, "unit": unit}
    signature = sign(
        private_pem, serialize(telemetry_signable_dict(device_id, timestamp, payload))
    )
    return {
        "device_id": device_id,
        "timestamp": timestamp,
        "payload": payload,
        "signature": signature,
    }


# --- registration ---------------------------------------------------------

def test_register_device_success(client):
    _, public_pem = generate_key_pair()
    resp = client.post(
        f"{API_PREFIX}/devices/register",
        json={"device_id": "temp-01", "public_key": public_pem},
    )
    assert resp.status_code == 201
    assert resp.json()["device_id"] == "temp-01"


def test_register_invalid_public_key_returns_400(client):
    resp = client.post(
        f"{API_PREFIX}/devices/register",
        json={"device_id": "temp-01", "public_key": "not-a-real-pem"},
    )
    assert resp.status_code == 400


def test_register_duplicate_device_returns_409(client):
    _, public_pem = generate_key_pair()
    body = {"device_id": "dup", "public_key": public_pem}
    assert client.post(f"{API_PREFIX}/devices/register", json=body).status_code == 201
    assert client.post(f"{API_PREFIX}/devices/register", json=body).status_code == 409


def test_register_missing_fields_returns_422(client):
    resp = client.post(f"{API_PREFIX}/devices/register", json={"device_id": "x"})
    assert resp.status_code == 422


# --- telemetry ingestion --------------------------------------------------

def test_telemetry_success_adds_block(client):
    private_pem = register_device(client, "temp-01")
    resp = client.post(
        f"{API_PREFIX}/telemetry", json=signed_telemetry("temp-01", private_pem)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["block_index"] == 1
    assert body["chain_length"] == 2  # genesis + 1


def test_telemetry_unregistered_device_returns_404(client):
    private_pem, _ = generate_key_pair()
    resp = client.post(
        f"{API_PREFIX}/telemetry", json=signed_telemetry("ghost", private_pem)
    )
    assert resp.status_code == 404


def test_telemetry_invalid_signature_returns_401(client):
    register_device(client, "temp-01")
    # Sign with a DIFFERENT key than the one registered for temp-01.
    wrong_private, _ = generate_key_pair()
    resp = client.post(
        f"{API_PREFIX}/telemetry", json=signed_telemetry("temp-01", wrong_private)
    )
    assert resp.status_code == 401


def test_telemetry_tampered_payload_returns_401(client):
    private_pem = register_device(client, "temp-01")
    body = signed_telemetry("temp-01", private_pem, value=21.5)
    body["payload"]["value"] = 99.9  # tamper AFTER signing
    resp = client.post(f"{API_PREFIX}/telemetry", json=body)
    assert resp.status_code == 401


def test_telemetry_malformed_body_returns_422(client):
    register_device(client, "temp-01")
    bad = signed_telemetry("temp-01", generate_key_pair()[0])
    del bad["signature"]  # required field missing
    resp = client.post(f"{API_PREFIX}/telemetry", json=bad)
    assert resp.status_code == 422


def test_telemetry_is_persisted(client):
    private_pem = register_device(client, "temp-01")
    client.post(f"{API_PREFIX}/telemetry", json=signed_telemetry("temp-01", private_pem))
    # Reload straight from the store to confirm it was written to disk.
    reloaded = client.app.state.store.load()
    assert len(reloaded) == 2
    assert reloaded.blocks[1].transactions[0]["device_id"] == "temp-01"


def test_stored_transaction_keeps_signature(client):
    private_pem = register_device(client, "temp-01")
    client.post(f"{API_PREFIX}/telemetry", json=signed_telemetry("temp-01", private_pem))
    resp = client.get(f"{API_PREFIX}/chain")
    tx = resp.json()["blocks"][1]["transactions"][0]
    assert tx["device_id"] == "temp-01"
    assert "signature" in tx


# --- chain & validate -----------------------------------------------------

def test_get_chain_returns_genesis(client):
    resp = client.get(f"{API_PREFIX}/chain")
    assert resp.status_code == 200
    body = resp.json()
    assert body["difficulty"] == 2
    assert body["length"] == 1
    assert body["blocks"][0]["index"] == 0


def test_get_chain_grows_after_telemetry(client):
    private_pem = register_device(client, "temp-01")
    client.post(f"{API_PREFIX}/telemetry", json=signed_telemetry("temp-01", private_pem))
    assert client.get(f"{API_PREFIX}/chain").json()["length"] == 2


def test_validate_endpoint_reports_valid(client):
    private_pem = register_device(client, "temp-01")
    client.post(f"{API_PREFIX}/telemetry", json=signed_telemetry("temp-01", private_pem))
    resp = client.get(f"{API_PREFIX}/validate")
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_validate_endpoint_detects_tampering(client):
    private_pem = register_device(client, "temp-01")
    client.post(f"{API_PREFIX}/telemetry", json=signed_telemetry("temp-01", private_pem))
    # Tamper with the in-memory chain, then ask the endpoint to validate.
    client.app.state.chain.blocks[1].transactions = [{"hacked": True}]
    body = client.get(f"{API_PREFIX}/validate").json()
    assert body["valid"] is False
    assert body["block_index"] == 1
    assert body["reason"]


# --- device history -------------------------------------------------------

def test_device_history_returns_records(client):
    private_pem = register_device(client, "temp-01")
    client.post(
        f"{API_PREFIX}/telemetry",
        json=signed_telemetry("temp-01", private_pem, value=21.5, timestamp=1000.0),
    )
    client.post(
        f"{API_PREFIX}/telemetry",
        json=signed_telemetry("temp-01", private_pem, value=22.0, timestamp=1001.0),
    )
    resp = client.get(f"{API_PREFIX}/device/temp-01")
    assert resp.status_code == 200
    body = resp.json()
    assert body["device_id"] == "temp-01"
    assert body["total_records"] == 2
    assert all(r["device_id"] == "temp-01" for r in body["records"])


def test_device_history_empty_when_no_telemetry(client):
    register_device(client, "temp-01")
    resp = client.get(f"{API_PREFIX}/device/temp-01")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_records"] == 0
    assert body["records"] == []


def test_device_history_unregistered_returns_404(client):
    resp = client.get(f"{API_PREFIX}/device/ghost")
    assert resp.status_code == 404


def test_device_history_filters_by_device(client):
    private_a = register_device(client, "dev-A")
    private_b = register_device(client, "dev-B")
    client.post(f"{API_PREFIX}/telemetry", json=signed_telemetry("dev-A", private_a))
    client.post(f"{API_PREFIX}/telemetry", json=signed_telemetry("dev-B", private_b))
    body = client.get(f"{API_PREFIX}/device/dev-A").json()
    assert body["total_records"] == 1
    assert body["records"][0]["device_id"] == "dev-A"
