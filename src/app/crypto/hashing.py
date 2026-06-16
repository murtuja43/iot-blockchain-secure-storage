"""SHA-256 hashing utilities.

SHA-256 is a cryptographic hash function: it maps any input to a fixed 256-bit
(32-byte / 64-hex-character) "digest". The properties we rely on:

  * Deterministic        - the same input always yields the same digest.
  * One-way              - you cannot feasibly reverse a digest to its input.
  * Avalanche            - flipping one input bit changes ~half the output bits.
  * Collision-resistant  - infeasible to find two inputs with the same digest.

In this project SHA-256 does two jobs:
  1. It produces each block's ``hash`` (and links blocks via ``previous_hash``),
     which is exactly what makes the chain tamper-evident.
  2. It is the digest algorithm underneath our ECDSA signatures.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.crypto.serialization import serialize


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 digest of raw ``bytes`` as a 64-character hex string."""
    return hashlib.sha256(data).hexdigest()


def hash_object(data: Any) -> str:
    """Hash an arbitrary (JSON-serializable) object deterministically.

    The object is first canonicalized to bytes (see ``serialization.serialize``)
    so logically-equal objects always hash to the same value regardless of dict
    key order. Returns a 64-character hex digest.
    """
    return sha256_hex(serialize(data))
