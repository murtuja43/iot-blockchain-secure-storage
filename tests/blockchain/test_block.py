"""Unit tests for the Block data structure."""

from app.blockchain.block import Block


def make_block(**overrides):
    base = dict(
        index=1,
        timestamp=1000.0,
        transactions=[{"device_id": "s1", "value": 10}],
        previous_hash="abc",
        nonce=0,
    )
    base.update(overrides)
    return Block(**base)


def test_compute_hash_is_deterministic():
    assert make_block().compute_hash() == make_block().compute_hash()


def test_hash_excludes_the_hash_field():
    # Storing a value in .hash must not change what compute_hash() returns,
    # because a block's hash cannot be an input to its own computation.
    b = make_block()
    before = b.compute_hash()
    b.hash = "anything"
    assert b.compute_hash() == before


def test_changing_nonce_changes_hash():
    b = make_block(nonce=0)
    h0 = b.compute_hash()
    b.nonce = 1
    assert b.compute_hash() != h0


def test_changing_any_field_changes_hash():
    base_hash = make_block().compute_hash()
    assert make_block(index=2).compute_hash() != base_hash
    assert make_block(timestamp=2000.0).compute_hash() != base_hash
    assert make_block(transactions=[{"x": 1}]).compute_hash() != base_hash
    assert make_block(previous_hash="def").compute_hash() != base_hash


def test_hash_is_64_hex_chars():
    assert len(make_block().compute_hash()) == 64


def test_to_dict_contains_all_six_fields():
    b = make_block()
    b.hash = b.compute_hash()
    assert set(b.to_dict()) == {
        "index",
        "timestamp",
        "transactions",
        "previous_hash",
        "nonce",
        "hash",
    }


def test_to_dict_from_dict_round_trip():
    b = make_block()
    b.hash = b.compute_hash()
    assert Block.from_dict(b.to_dict()) == b
