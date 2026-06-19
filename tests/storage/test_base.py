"""Unit tests for the abstract storage interface."""

import pytest

from app.storage.base import BlockchainRepository


def test_abstract_repository_cannot_be_instantiated():
    # BlockchainRepository declares abstract methods, so it must not be usable
    # directly - only concrete subclasses (e.g. JsonBlockchainStore) can be.
    with pytest.raises(TypeError):
        BlockchainRepository()
