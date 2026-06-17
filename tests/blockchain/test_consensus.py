"""Unit tests for Proof-of-Work consensus."""

import pytest

from app.blockchain.block import Block
from app.blockchain.consensus import is_valid_proof, mine_block


def make_block():
    return Block(index=1, timestamp=1000.0, transactions=[], previous_hash="0" * 64)


def test_is_valid_proof_checks_leading_zeros():
    assert is_valid_proof("000abc", 3) is True
    assert is_valid_proof("000abc", 4) is False
    assert is_valid_proof("00abc", 2) is True


def test_difficulty_zero_accepts_any_hash():
    assert is_valid_proof("ffffff", 0) is True


def test_negative_difficulty_raises():
    with pytest.raises(ValueError):
        is_valid_proof("abc", -1)


@pytest.mark.parametrize("difficulty", [1, 2, 3])
def test_mine_block_produces_valid_proof(difficulty):
    mined = mine_block(make_block(), difficulty)
    assert mined.hash.startswith("0" * difficulty)
    assert is_valid_proof(mined.hash, difficulty)


def test_mine_block_stores_consistent_hash():
    block = mine_block(make_block(), 2)
    # The stored hash must equal a fresh recomputation from the block's fields.
    assert block.hash == block.compute_hash()


def test_mine_block_negative_difficulty_raises():
    with pytest.raises(ValueError):
        mine_block(make_block(), -1)
