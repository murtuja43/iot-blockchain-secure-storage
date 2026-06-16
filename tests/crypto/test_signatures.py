"""Unit tests for ECDSA key generation, signing, and verification."""

import pytest

from app.crypto.serialization import serialize
from app.crypto.signatures import (
    generate_key_pair,
    load_private_key,
    serialize_private_key,
    serialize_public_key,
    sign,
    verify,
)


@pytest.fixture
def key_pair():
    """A fresh (private_pem, public_pem) pair for each test that needs one."""
    return generate_key_pair()


def test_generate_key_pair_returns_two_pems(key_pair):
    private_pem, public_pem = key_pair
    assert "PRIVATE KEY" in private_pem
    assert "PUBLIC KEY" in public_pem
    assert private_pem != public_pem


def test_each_key_pair_is_unique():
    priv1, _ = generate_key_pair()
    priv2, _ = generate_key_pair()
    assert priv1 != priv2


def test_sign_returns_valid_hex(key_pair):
    private_pem, _ = key_pair
    sig = sign(private_pem, b"hello")
    assert isinstance(sig, str)
    bytes.fromhex(sig)  # raises if the string is not valid hex


def test_sign_then_verify_succeeds(key_pair):
    private_pem, public_pem = key_pair
    data = b"telemetry-payload"
    sig = sign(private_pem, data)
    assert verify(public_pem, data, sig) is True


def test_verify_fails_for_tampered_data(key_pair):
    private_pem, public_pem = key_pair
    sig = sign(private_pem, b"original")
    assert verify(public_pem, b"tampered", sig) is False


def test_verify_fails_with_wrong_public_key(key_pair):
    private_pem, _ = key_pair
    _, other_public_pem = generate_key_pair()
    data = b"data"
    sig = sign(private_pem, data)
    assert verify(other_public_pem, data, sig) is False


def test_verify_fails_for_tampered_signature(key_pair):
    private_pem, public_pem = key_pair
    data = b"data"
    sig = sign(private_pem, data)
    flipped = sig[:-1] + ("0" if sig[-1] != "0" else "1")  # change last hex digit
    assert verify(public_pem, data, flipped) is False


def test_verify_returns_false_for_malformed_signature(key_pair):
    _, public_pem = key_pair
    assert verify(public_pem, b"data", "not-hex!!") is False  # not hex at all
    assert verify(public_pem, b"data", "abcd") is False  # valid hex, wrong sig


def test_ecdsa_signatures_are_nondeterministic_but_both_valid(key_pair):
    # ECDSA uses a random nonce, so two signatures over the same data differ,
    # yet both verify. (This is expected, not a bug.)
    private_pem, public_pem = key_pair
    data = b"same-data"
    sig1 = sign(private_pem, data)
    sig2 = sign(private_pem, data)
    assert sig1 != sig2
    assert verify(public_pem, data, sig1)
    assert verify(public_pem, data, sig2)


def test_pem_round_trip_is_stable(key_pair):
    private_pem, public_pem = key_pair
    loaded = load_private_key(private_pem)
    assert serialize_private_key(loaded) == private_pem
    assert serialize_public_key(loaded.public_key()) == public_pem


def test_end_to_end_telemetry_signing(key_pair):
    """The real use case: sign a telemetry dict, then verify after the server
    reconstructs the same logical data in a different key order."""
    private_pem, public_pem = key_pair

    reading = {
        "device_id": "temp-001",
        "timestamp": "2026-01-01T00:00:00Z",
        "payload": {"value": 21.5, "unit": "C"},
    }
    signature = sign(private_pem, serialize(reading))

    # Server side: same data, different key order -> must still verify.
    received = {
        "payload": {"unit": "C", "value": 21.5},
        "timestamp": "2026-01-01T00:00:00Z",
        "device_id": "temp-001",
    }
    assert verify(public_pem, serialize(received), signature) is True

    # Altering the payload value must break verification.
    tampered = dict(received)
    tampered["payload"] = {"unit": "C", "value": 99.9}
    assert verify(public_pem, serialize(tampered), signature) is False
