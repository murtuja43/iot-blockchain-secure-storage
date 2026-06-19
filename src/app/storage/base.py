"""Abstract storage interface for the blockchain (the Repository pattern).

The rest of the system should be able to save and load the chain without caring
*how* it is stored - JSON file today, SQLite or a database tomorrow. We express
that with an abstract base class: any concrete store (e.g. ``JsonBlockchainStore``)
implements ``save``, ``load``, and ``exists``, and code elsewhere depends only on
this interface.

This is "dependency inversion": high-level code depends on an abstraction, not on
a concrete file format. Swapping storage backends becomes a one-line change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.blockchain.chain import Blockchain


class StorageError(Exception):
    """Raised when the chain cannot be saved or loaded (I/O, corruption, bad data)."""


class BlockchainRepository(ABC):
    """Interface every blockchain storage backend must implement."""

    @abstractmethod
    def save(self, chain: Blockchain) -> None:
        """Persist the entire chain, overwriting any previous saved state."""

    @abstractmethod
    def load(self) -> Blockchain:
        """Load and return the persisted chain.

        Implementations must raise ``StorageError`` if no saved chain exists or
        the stored data is corrupted/invalid.
        """

    @abstractmethod
    def exists(self) -> bool:
        """Return True if a persisted chain is present."""

    def load_or_create(self, difficulty: int | None = None) -> Blockchain:
        """Load the saved chain, or create+save a brand-new one if none exists.

        This is the convenient startup path: it makes "first run" (no file yet)
        and "restart" (file present) behave the same to the caller. It is a
        concrete helper because it works for ANY backend via ``exists``/``load``/
        ``save``.
        """
        if self.exists():
            return self.load()
        chain = Blockchain() if difficulty is None else Blockchain(difficulty=difficulty)
        self.save(chain)
        return chain
