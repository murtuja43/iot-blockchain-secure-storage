"""JSON-file persistence for the blockchain.

Stores the whole chain as a single human-readable JSON file. Two design points
worth understanding:

  * Atomic writes - we write to a temporary file first and then ``os.replace``
    it over the real one. ``os.replace`` is atomic on the same filesystem, so a
    crash mid-write can never leave a half-written, corrupted chain file.

  * Pretty vs. canonical - this file is indented for humans (and so you can open
    it and tamper with it to watch validation catch you). That formatting is
    purely cosmetic: block *hashes* are computed by the canonical serializer in
    ``crypto/serialization.py``, never from this file's layout, so indentation
    does not affect integrity.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.blockchain.chain import Blockchain
from app.config import CHAIN_FILE
from app.storage.base import BlockchainRepository, StorageError


class JsonBlockchainStore(BlockchainRepository):
    """Persists a ``Blockchain`` to/from a JSON file."""

    def __init__(self, file_path: Path | str = CHAIN_FILE) -> None:
        self.file_path = Path(file_path)

    def exists(self) -> bool:
        return self.file_path.is_file()

    def save(self, chain: Blockchain) -> None:
        """Write the chain to disk atomically, creating the folder if needed."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self.file_path.with_name(self.file_path.name + ".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(chain.to_dict(), f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.file_path)  # atomic swap into place
        except OSError as e:
            raise StorageError(f"could not write blockchain file: {e}") from e

    def load(self) -> Blockchain:
        """Read, parse, and rebuild the chain, failing gracefully on bad data."""
        if not self.exists():
            raise StorageError(f"no blockchain file found at {self.file_path}")

        # 1. Read + parse JSON (handles a corrupted / non-JSON file).
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise StorageError(
                f"blockchain file is corrupted (invalid JSON): {e}"
            ) from e
        except OSError as e:
            raise StorageError(f"could not read blockchain file: {e}") from e

        # 2. Rebuild the domain objects (handles wrong/missing fields).
        try:
            return Blockchain.from_dict(data)
        except (ValueError, KeyError, TypeError) as e:
            raise StorageError(f"invalid blockchain structure: {e}") from e
