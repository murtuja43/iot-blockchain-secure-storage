"""FastAPI application entry point.

``create_app`` is an application factory: it builds a fresh FastAPI app, wires in
the routes, and uses a lifespan handler to set up shared state at startup -
loading the blockchain from storage (or creating a new one on first run) and
initialising the device registry and a write lock.

The factory accepts optional ``store``/``registry``/``difficulty`` overrides so
tests can inject a temp-file store and a low difficulty without touching disk.

Run the server with:
    uvicorn app.api.main:app --app-dir src --host 127.0.0.1 --port 8000
then open http://127.0.0.1:8000/docs for interactive API docs.
"""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config
from app.api.routes import router
from app.devices.registry import DeviceRegistry
from app.storage.base import BlockchainRepository
from app.storage.json_store import JsonBlockchainStore


def create_app(
    *,
    store: BlockchainRepository | None = None,
    registry: DeviceRegistry | None = None,
    difficulty: int | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: choose a store, load (or create) the chain, init registry.
        active_store = store
        if active_store is None:
            config.ensure_directories()
            active_store = JsonBlockchainStore()

        app.state.store = active_store
        app.state.chain = active_store.load_or_create(difficulty=difficulty)
        app.state.registry = registry if registry is not None else DeviceRegistry()
        app.state.lock = threading.Lock()
        yield
        # Shutdown: nothing to clean up (chain is already persisted on each write).

    app = FastAPI(
        title=config.API_TITLE,
        version=config.API_VERSION,
        lifespan=lifespan,
    )
    app.include_router(router, prefix=config.API_PREFIX)
    return app


# Module-level app for `uvicorn app.api.main:app`.
app = create_app()
