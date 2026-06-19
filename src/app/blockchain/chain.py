"""The blockchain: an ordered, append-only list of mined blocks.

Responsibilities (Phase 2):
  * create the genesis (first) block automatically,
  * append new blocks, each mined via Proof-of-Work,
  * keep blocks correctly ordered and linked (each ``previous_hash`` points at
    the prior block's ``hash``).

Full integrity validation / tamper detection arrives in Phase 3.
"""

from __future__ import annotations

import time
from typing import Any

from app.blockchain.block import Block
from app.blockchain.consensus import mine_block
from app.config import POW_DIFFICULTY

# Conventional previous_hash for the genesis block (it has no predecessor).
GENESIS_PREVIOUS_HASH = "0" * 64


class Blockchain:
    """An in-memory chain of blocks secured by Proof-of-Work."""

    def __init__(self, difficulty: int = POW_DIFFICULTY) -> None:
        self.difficulty = difficulty
        self.blocks: list[Block] = []
        self._create_genesis_block()

    def _create_genesis_block(self) -> None:
        """Create and mine the first block, which anchors the entire chain."""
        genesis = Block(
            index=0,
            timestamp=time.time(),
            transactions=[],
            previous_hash=GENESIS_PREVIOUS_HASH,
        )
        mine_block(genesis, self.difficulty)
        self.blocks.append(genesis)

    @property
    def last_block(self) -> Block:
        """The most recent block in the chain (the chain's tip)."""
        return self.blocks[-1]

    def add_block(
        self, transactions: list[Any], timestamp: float | None = None
    ) -> Block:
        """Create, mine, and append a new block carrying ``transactions``.

        The new block takes the next sequential index and links to the current
        tip via ``previous_hash``. ``timestamp`` may be supplied for
        reproducible tests/demos; otherwise the current time is used.
        """
        new_block = Block(
            index=self.last_block.index + 1,
            timestamp=time.time() if timestamp is None else timestamp,
            transactions=transactions,
            previous_hash=self.last_block.hash,
        )
        mine_block(new_block, self.difficulty)
        self.blocks.append(new_block)
        return new_block

    def __len__(self) -> int:
        return len(self.blocks)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the whole chain to a plain dictionary."""
        return {
            "difficulty": self.difficulty,
            "blocks": [block.to_dict() for block in self.blocks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Blockchain":
        """Rebuild a chain from ``to_dict()`` output (used by the storage layer).

        Unlike ``__init__``, this does NOT create a fresh genesis block - the
        blocks are restored exactly as they were saved. ``cls.__new__`` builds
        the instance without running ``__init__`` so that no throwaway genesis
        is mined during restoration.

        Raises ``ValueError`` if the required keys are missing, so callers can
        turn malformed data into a clear error.
        """
        if not isinstance(data, dict) or "difficulty" not in data or "blocks" not in data:
            raise ValueError(
                "blockchain data must be an object with 'difficulty' and 'blocks'"
            )
        chain = cls.__new__(cls)
        chain.difficulty = data["difficulty"]
        chain.blocks = [Block.from_dict(b) for b in data["blocks"]]
        return chain
