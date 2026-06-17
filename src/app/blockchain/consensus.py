"""Proof-of-Work consensus: mining and proof validation.

Proof-of-Work (PoW) makes adding a block *deliberately expensive*. To add a
block you must find a ``nonce`` such that the block's SHA-256 hash begins with a
required number of leading zeros (the "difficulty"). Because SHA-256 output is
unpredictable, the only known way to find such a nonce is to try values one
after another - that brute-force effort is the "work" that secures the chain.
Rewriting an old block would mean redoing the work for it AND every block after
it, which is what makes tampering impractical.

Difficulty here = the number of leading '0' hex characters required. Each extra
zero makes a valid hash ~16x rarer (one hex digit = 4 bits), so mining time
grows exponentially with difficulty.
"""

from __future__ import annotations

from app.blockchain.block import Block


def is_valid_proof(block_hash: str, difficulty: int) -> bool:
    """Return True if ``block_hash`` satisfies the difficulty requirement.

    The requirement is simply: the hash must start with ``difficulty`` zeros.
    """
    if difficulty < 0:
        raise ValueError("difficulty must be non-negative")
    return block_hash.startswith("0" * difficulty)


def mine_block(block: Block, difficulty: int) -> Block:
    """Mine ``block`` in place: find a nonce whose hash meets the difficulty.

    Starts the nonce at 0 and increments it, recomputing the hash each time,
    until ``is_valid_proof`` succeeds. Stores the winning nonce and hash on the
    block, then returns it.
    """
    if difficulty < 0:
        raise ValueError("difficulty must be non-negative")

    block.nonce = 0
    computed = block.compute_hash()
    while not is_valid_proof(computed, difficulty):
        block.nonce += 1
        computed = block.compute_hash()

    block.hash = computed
    return block
