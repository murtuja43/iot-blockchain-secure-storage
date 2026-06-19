"""Unit tests for JSON blockchain persistence."""

import json

import pytest

from app.blockchain.chain import Blockchain
from app.blockchain.validation import validate_chain
from app.storage.base import StorageError
from app.storage.json_store import JsonBlockchainStore


def make_chain(num_blocks=2, difficulty=2):
    chain = Blockchain(difficulty=difficulty)
    for i in range(num_blocks):
        chain.add_block([{"device_id": f"s{i}", "value": i}])
    return chain


# --- Save -----------------------------------------------------------------

def test_save_creates_file(tmp_path):
    path = tmp_path / "chain.json"
    store = JsonBlockchainStore(path)
    assert not store.exists()
    store.save(make_chain())
    assert store.exists()
    assert path.is_file()


def test_save_creates_missing_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "chain.json"
    store = JsonBlockchainStore(path)
    store.save(make_chain())
    assert path.is_file()


# --- Load / round trip ----------------------------------------------------

def test_load_returns_equivalent_chain(tmp_path):
    store = JsonBlockchainStore(tmp_path / "chain.json")
    original = make_chain()
    store.save(original)
    loaded = store.load()
    assert loaded.to_dict() == original.to_dict()


def test_save_load_multiple_blocks(tmp_path):
    store = JsonBlockchainStore(tmp_path / "chain.json")
    original = make_chain(num_blocks=5)
    store.save(original)
    loaded = store.load()
    assert len(loaded) == len(original) == 6  # 5 + genesis
    for orig_block, new_block in zip(original.blocks, loaded.blocks):
        assert new_block.to_dict() == orig_block.to_dict()


def test_loaded_chain_still_validates(tmp_path):
    store = JsonBlockchainStore(tmp_path / "chain.json")
    store.save(make_chain(num_blocks=3))
    loaded = store.load()
    assert validate_chain(loaded).is_valid is True


def test_difficulty_is_preserved(tmp_path):
    store = JsonBlockchainStore(tmp_path / "chain.json")
    store.save(make_chain(difficulty=3))
    assert store.load().difficulty == 3


def test_persistence_survives_simulated_restart(tmp_path):
    path = tmp_path / "chain.json"
    # First "run": build and save.
    chain = make_chain(num_blocks=2)
    JsonBlockchainStore(path).save(chain)
    # Second "run": a brand-new store object loads the same file.
    restored = JsonBlockchainStore(path).load()
    assert restored.to_dict() == chain.to_dict()
    assert validate_chain(restored).is_valid


# --- Error handling -------------------------------------------------------

def test_load_missing_file_raises_clear_error(tmp_path):
    store = JsonBlockchainStore(tmp_path / "does_not_exist.json")
    with pytest.raises(StorageError, match="no blockchain file"):
        store.load()


def test_corrupted_json_raises_clear_error(tmp_path):
    path = tmp_path / "chain.json"
    path.write_text("{ this is not valid json ")
    store = JsonBlockchainStore(path)
    with pytest.raises(StorageError, match="corrupted"):
        store.load()


def test_invalid_structure_missing_keys_raises(tmp_path):
    path = tmp_path / "chain.json"
    path.write_text(json.dumps({"unexpected": "data"}))
    store = JsonBlockchainStore(path)
    with pytest.raises(StorageError, match="invalid blockchain structure"):
        store.load()


def test_invalid_block_structure_raises(tmp_path):
    path = tmp_path / "chain.json"
    # 'blocks' present but a block is missing required fields.
    path.write_text(json.dumps({"difficulty": 2, "blocks": [{"index": 0}]}))
    store = JsonBlockchainStore(path)
    with pytest.raises(StorageError, match="invalid blockchain structure"):
        store.load()


def test_file_tampering_is_detected_after_load(tmp_path):
    """Persistence + Phase 3 together: editing the file on disk is caught."""
    path = tmp_path / "chain.json"
    store = JsonBlockchainStore(path)
    store.save(make_chain(num_blocks=1))

    # Simulate an attacker editing the stored JSON directly.
    data = json.loads(path.read_text())
    data["blocks"][1]["transactions"] = [{"device_id": "s0", "value": 9999}]
    path.write_text(json.dumps(data))

    loaded = store.load()  # loads fine (structure is valid)...
    assert validate_chain(loaded).is_valid is False  # ...but integrity fails


# --- load_or_create -------------------------------------------------------

def test_load_or_create_creates_when_missing(tmp_path):
    path = tmp_path / "chain.json"
    store = JsonBlockchainStore(path)
    chain = store.load_or_create(difficulty=2)
    assert path.is_file()          # it was created and saved
    assert len(chain) == 1         # genesis only
    assert validate_chain(chain).is_valid


def test_load_or_create_loads_existing(tmp_path):
    path = tmp_path / "chain.json"
    store = JsonBlockchainStore(path)
    original = make_chain(num_blocks=3)
    store.save(original)
    loaded = store.load_or_create(difficulty=2)
    assert loaded.to_dict() == original.to_dict()  # existing chain, not a fresh one
