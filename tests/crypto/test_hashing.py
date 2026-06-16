"""Unit tests for SHA-256 hashing utilities."""

from app.crypto.hashing import hash_object, sha256_hex

# Known-answer vectors from the SHA-256 standard (independently verifiable).
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_known_vector_empty_input():
    assert sha256_hex(b"") == EMPTY_SHA256


def test_known_vector_abc():
    assert sha256_hex(b"abc") == ABC_SHA256


def test_digest_is_64_lowercase_hex_chars():
    digest = sha256_hex(b"anything")
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_hash_object_is_deterministic():
    obj = {"device_id": "s1", "value": 10}
    assert hash_object(obj) == hash_object(obj)


def test_hash_object_ignores_key_order():
    assert hash_object({"a": 1, "b": 2}) == hash_object({"b": 2, "a": 1})


def test_hash_object_changes_when_data_changes():
    assert hash_object({"value": 10}) != hash_object({"value": 11})


def test_avalanche_small_change_large_difference():
    # A one-character change should scramble a large fraction of the digest.
    h1 = sha256_hex(b"hello")
    h2 = sha256_hex(b"hellp")
    differing = sum(1 for x, y in zip(h1, h2) if x != y)
    assert differing > 20
