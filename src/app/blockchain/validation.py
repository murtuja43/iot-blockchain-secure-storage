"""Full-chain integrity validation and tamper detection.

This module answers one question: *has the chain been tampered with?* It walks
the chain from the genesis block to the tip and checks four independent things
for every block:

  1. Hash integrity - the block's stored ``hash`` must equal a fresh
     recomputation from its current contents. If any field was edited, the
     recomputed hash will differ, so this catches data tampering.
  2. Proof-of-Work  - the stored hash must still satisfy the difficulty
     requirement (enough leading zeros). This catches blocks that were edited
     and re-hashed but not re-mined.
  3. Link integrity - each block's ``previous_hash`` must equal the actual hash
     of the block before it. This is the "chain" in blockchain.
  4. Ordering        - indices must be sequential (genesis = 0, then +1 each).

The genesis block gets two extra checks (index 0 and the all-zero
``previous_hash``) because it has no predecessor to link to.

The result is a ``ValidationResult`` carrying a boolean plus a human-readable
reason and the offending block index - exactly what the GET /validate endpoint
will return in Phase 5.

Note: verifying each transaction's *digital signature* needs the device public
keys, which arrive with the device registry in Phase 5; that layer is added on
top of this structural validation later.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.block import Block
from app.blockchain.chain import GENESIS_PREVIOUS_HASH, Blockchain
from app.blockchain.consensus import is_valid_proof


@dataclass
class ValidationResult:
    """Outcome of validating a chain (or a single block).

    ``is_valid``    - True if everything checked out.
    ``reason``      - human-readable explanation (why it failed, or "chain is valid").
    ``block_index`` - index of the offending block, when applicable.
    """

    is_valid: bool
    reason: str | None = None
    block_index: int | None = None

    def __bool__(self) -> bool:
        # Lets callers write `if validate_chain(c): ...`
        return self.is_valid


def _check_block_integrity(block: Block, difficulty: int) -> ValidationResult:
    """Check a single block's own hash integrity and proof-of-work.

    Hash integrity is checked BEFORE proof-of-work on purpose: if the contents
    were edited, the recomputed hash won't match the stored one, and we want to
    report that as data tampering rather than as a PoW failure.
    """
    recomputed = block.compute_hash()
    if block.hash != recomputed:
        return ValidationResult(
            False,
            f"block {block.index}: stored hash does not match recomputed hash "
            f"(block contents were modified)",
            block.index,
        )
    if not is_valid_proof(block.hash, difficulty):
        return ValidationResult(
            False,
            f"block {block.index}: hash does not satisfy proof-of-work "
            f"difficulty {difficulty}",
            block.index,
        )
    return ValidationResult(True)


def _check_genesis(block: Block, difficulty: int) -> ValidationResult:
    """Validate the genesis block (the chain's anchor)."""
    if block.index != 0:
        return ValidationResult(
            False, "genesis block: index must be 0", 0
        )
    if block.previous_hash != GENESIS_PREVIOUS_HASH:
        return ValidationResult(
            False,
            "genesis block: previous_hash must be the all-zero hash",
            0,
        )
    return _check_block_integrity(block, difficulty)


def validate_chain(chain: Blockchain) -> ValidationResult:
    """Validate an entire chain from the genesis block to the tip.

    Returns a ``ValidationResult``. Validation stops and reports at the FIRST
    problem found, since one broken block invalidates everything after it.
    """
    blocks = chain.blocks
    difficulty = chain.difficulty

    if not blocks:
        return ValidationResult(False, "chain is empty (no genesis block)", None)

    # 1. The genesis block must be well-formed and intact.
    genesis_result = _check_genesis(blocks[0], difficulty)
    if not genesis_result:
        return genesis_result

    # 2. Every subsequent block: ordering, link, then own integrity.
    for i in range(1, len(blocks)):
        block = blocks[i]
        previous = blocks[i - 1]

        if block.index != previous.index + 1:
            return ValidationResult(
                False,
                f"block {block.index}: index out of order "
                f"(expected {previous.index + 1})",
                block.index,
            )

        if block.previous_hash != previous.hash:
            return ValidationResult(
                False,
                f"block {block.index}: previous_hash does not match the hash of "
                f"block {previous.index} (chain link broken)",
                block.index,
            )

        block_result = _check_block_integrity(block, difficulty)
        if not block_result:
            return block_result

    return ValidationResult(True, "chain is valid")
