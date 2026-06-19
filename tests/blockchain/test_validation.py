"""Unit tests for chain validation and tamper detection."""

from app.blockchain.chain import Blockchain
from app.blockchain.validation import validate_chain


def make_chain(num_blocks=3, difficulty=2):
    chain = Blockchain(difficulty=difficulty)
    for i in range(num_blocks):
        chain.add_block([{"device_id": f"s{i}", "value": i}])
    return chain


# --- Happy path -----------------------------------------------------------

def test_valid_chain_passes():
    result = validate_chain(make_chain())
    assert result.is_valid is True
    assert bool(result) is True


def test_validation_result_is_truthy_when_valid_falsy_when_invalid():
    chain = make_chain()
    assert validate_chain(chain)  # truthy
    chain.blocks[1].transactions = [{"hacked": True}]
    assert not validate_chain(chain)  # falsy


def test_chain_stays_valid_after_adding_blocks():
    chain = Blockchain(difficulty=2)
    assert validate_chain(chain).is_valid
    chain.add_block([{"x": 1}])
    assert validate_chain(chain).is_valid
    chain.add_block([{"y": 2}])
    assert validate_chain(chain).is_valid


# --- Tamper detection -----------------------------------------------------

def test_tampered_transaction_is_detected():
    chain = make_chain()
    chain.blocks[2].transactions = [{"device_id": "s2", "value": 9999}]
    result = validate_chain(chain)
    assert result.is_valid is False
    assert result.block_index == 2
    assert "hash" in result.reason.lower()


def test_tampered_block_hash_is_detected():
    chain = make_chain()
    chain.blocks[1].hash = "0" * 64  # looks plausible but doesn't match contents
    result = validate_chain(chain)
    assert result.is_valid is False
    assert result.block_index == 1


def test_broken_previous_hash_link_is_detected():
    chain = make_chain()
    chain.blocks[2].previous_hash = "deadbeef"
    result = validate_chain(chain)
    assert result.is_valid is False
    assert result.block_index == 2
    assert "previous_hash" in result.reason or "link" in result.reason.lower()


def test_invalid_proof_of_work_is_detected():
    # Craft a block whose stored hash MATCHES its contents (so the hash-match
    # check passes) but does NOT meet the difficulty requirement.
    chain = make_chain(num_blocks=1, difficulty=2)
    block = chain.blocks[1]
    block.nonce = 0
    block.hash = block.compute_hash()
    while block.hash.startswith("00"):  # ensure it really fails difficulty 2
        block.nonce += 1
        block.hash = block.compute_hash()
    result = validate_chain(chain)
    assert result.is_valid is False
    assert "proof-of-work" in result.reason.lower() or "difficulty" in result.reason.lower()


def test_modifying_an_early_block_invalidates_whole_chain():
    chain = make_chain(num_blocks=4)
    # Edit an early block; later blocks are untouched but the chain must fail.
    chain.blocks[1].transactions = [{"tampered": True}]
    assert validate_chain(chain).is_valid is False


# --- Genesis corruption ---------------------------------------------------

def test_genesis_transaction_corruption_is_detected():
    chain = make_chain()
    chain.blocks[0].transactions = [{"injected": "data"}]
    result = validate_chain(chain)
    assert result.is_valid is False
    assert result.block_index == 0


def test_genesis_previous_hash_corruption_is_detected():
    chain = make_chain()
    chain.blocks[0].previous_hash = "1" * 64
    result = validate_chain(chain)
    assert result.is_valid is False
    assert result.block_index == 0
    assert "genesis" in result.reason.lower()


def test_genesis_index_corruption_is_detected():
    chain = make_chain()
    chain.blocks[0].index = 5
    result = validate_chain(chain)
    assert result.is_valid is False
    assert "genesis" in result.reason.lower()


# --- Edge case ------------------------------------------------------------

def test_empty_chain_is_invalid():
    chain = make_chain(num_blocks=0)
    chain.blocks = []
    result = validate_chain(chain)
    assert result.is_valid is False
    assert "empty" in result.reason.lower()
