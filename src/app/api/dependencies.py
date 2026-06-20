"""Shared FastAPI dependencies: typed accessors for application state.

The blockchain, storage backend, device registry, and a write lock are created
once at startup (see ``main.create_app``) and stored on ``app.state``. These
small ``Depends`` functions hand them to route handlers, which keeps the routes
free of global variables and easy to test with a swapped-in store/registry.
"""

from __future__ import annotations

import threading

from fastapi import Request

from app.blockchain.chain import Blockchain
from app.devices.registry import DeviceRegistry
from app.storage.base import BlockchainRepository


def get_chain(request: Request) -> Blockchain:
    return request.app.state.chain


def get_store(request: Request) -> BlockchainRepository:
    return request.app.state.store


def get_registry(request: Request) -> DeviceRegistry:
    return request.app.state.registry


def get_lock(request: Request) -> threading.Lock:
    return request.app.state.lock
