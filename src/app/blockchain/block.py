"""Block data structure for the blockchain.

A *block* is the unit of storage in a blockchain. It bundles a batch of
transactions together with metadata that (a) orders it within the chain and
(b) cryptographically ties it to the block before it.

Fields
------
index          Position in the chain (genesis = 0, then 1, 2, ...).
timestamp      Unix time (seconds) when the block was created.
transactions   The data carried by the block (here: IoT telemetry records).
previous_hash  Hash of the block immediately before this one - the "link".
nonce          A counter varied during mining until the hash meets difficulty.
hash           SHA-256 digest of all the fields above; the block's fingerprint.

The crucial idea: ``hash`` is computed FROM the other fields. Change any field
and the hash no longer matches what gets recomputed - which is exactly how
tampering is detected (Phase 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.crypto.hashing import hash_object


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: list[Any]
    previous_hash: str
    nonce: int = 0
    hash: str | None = None

    def hashable_contents(self) -> dict[str, Any]:
        """Return the fields the block hash is computed over.

        This deliberately EXCLUDES ``hash`` itself - a value cannot be an input
        to its own computation. ``nonce`` IS included, because mining works by
        changing the nonce until the resulting hash is acceptable.
        """
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }

    def compute_hash(self) -> str:
        """Compute this block's SHA-256 hash from its current contents."""
        return hash_object(self.hashable_contents())

    def to_dict(self) -> dict[str, Any]:
        """Full dictionary representation, including the stored ``hash``."""
        data = self.hashable_contents()
        data["hash"] = self.hash
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Block":
        """Rebuild a Block from a dictionary (inverse of ``to_dict``)."""
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            transactions=data["transactions"],
            previous_hash=data["previous_hash"],
            nonce=data["nonce"],
            hash=data.get("hash"),
        )
