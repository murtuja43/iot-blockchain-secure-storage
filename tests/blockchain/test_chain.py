"""Unit tests for the Blockchain container."""

from app.blockchain.chain import GENESIS_PREVIOUS_HASH, Blockchain


def test_new_chain_has_only_genesis():
    chain = Blockchain(difficulty=2)
    assert len(chain) == 1
    genesis = chain.blocks[0]
    assert genesis.index == 0
    assert genesis.previous_hash == GENESIS_PREVIOUS_HASH
    assert genesis.transactions == []


def test_genesis_satisfies_difficulty():
    chain = Blockchain(difficulty=2)
    assert chain.blocks[0].hash.startswith("00")


def test_add_block_increments_index_and_links():
    chain = Blockchain(difficulty=2)
    prev_hash = chain.last_block.hash
    block = chain.add_block([{"device_id": "s1", "value": 21}])
    assert block.index == 1
    assert block.previous_hash == prev_hash
    assert len(chain) == 2


def test_all_blocks_satisfy_difficulty():
    chain = Blockchain(difficulty=2)
    for i in range(3):
        chain.add_block([{"reading": i}])
    assert all(b.hash.startswith("00") for b in chain.blocks)


def test_blocks_are_linked_and_ordered():
    chain = Blockchain(difficulty=2)
    chain.add_block([{"a": 1}])
    chain.add_block([{"b": 2}])
    chain.add_block([{"c": 3}])
    assert [b.index for b in chain.blocks] == [0, 1, 2, 3]
    for i in range(1, len(chain)):
        assert chain.blocks[i].previous_hash == chain.blocks[i - 1].hash


def test_last_block_returns_tip():
    chain = Blockchain(difficulty=2)
    last = chain.add_block([{"x": 1}])
    assert chain.last_block is last


def test_transactions_are_stored():
    chain = Blockchain(difficulty=2)
    txs = [{"device_id": "s1", "value": 10}, {"device_id": "s2", "value": 20}]
    block = chain.add_block(txs)
    assert block.transactions == txs


def test_to_dict_structure():
    chain = Blockchain(difficulty=2)
    chain.add_block([{"x": 1}])
    d = chain.to_dict()
    assert d["difficulty"] == 2
    assert len(d["blocks"]) == 2
    assert d["blocks"][0]["index"] == 0


def test_custom_difficulty_is_applied():
    chain = Blockchain(difficulty=1)
    assert chain.last_block.hash.startswith("0")
