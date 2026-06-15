"""Central configuration for the IoT blockchain prototype.

Every tunable value lives here so the rest of the codebase never hard-codes a
path, port, or "magic number". The important knobs can be overridden with
environment variables, which keeps machine-specific settings out of the code
(this is the "12-factor config" idea: config comes from the environment).

Importing this module has NO side effects (it does not touch the filesystem).
Call ``ensure_directories()`` explicitly at startup when you actually need the
data folders to exist.
"""

from __future__ import annotations

import os
from pathlib import Path


def _get_int(name: str, default: int) -> int:
    """Read an integer from an environment variable, falling back to ``default``.

    A missing, blank, or non-numeric value safely returns the default instead
    of crashing the program at import time.
    """
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Filesystem paths
# ---------------------------------------------------------------------------
# This file is at <root>/src/app/config.py, so the project root is three
# parents up:  config.py -> app -> src -> <root>.
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
KEYS_DIR = DATA_DIR / "keys"            # server-side store of device public keys
CHAIN_FILE = DATA_DIR / "chain.json"    # JSON persistence for the blockchain

# ---------------------------------------------------------------------------
# Blockchain / consensus settings
# ---------------------------------------------------------------------------
# Proof-of-Work difficulty = number of leading zeros a valid block hash must
# have. Higher is more secure but exponentially slower to mine. Keep it low
# for demos; raise it to feel the cost of PoW.
POW_DIFFICULTY = _get_int("POW_DIFFICULTY", 3)

# How many pending transactions accumulate before a new block is mined.
# 1 = mine a block per reading (simplest); raise it to batch multiple
# transactions into a single block.
MEMPOOL_BLOCK_SIZE = _get_int("MEMPOOL_BLOCK_SIZE", 1)

# ---------------------------------------------------------------------------
# API settings
# ---------------------------------------------------------------------------
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = _get_int("API_PORT", 8000)
API_PREFIX = "/api/v1"                  # version prefix shared by all routes
API_TITLE = "IoT Blockchain Secure Storage"
API_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# IoT simulator settings
# ---------------------------------------------------------------------------
# Base URL the simulated devices POST their telemetry to.
API_BASE_URL = os.getenv("API_BASE_URL", f"http://{API_HOST}:{API_PORT}")

# Seconds each simulated device waits between transmissions.
TELEMETRY_INTERVAL_SECONDS = _get_int("TELEMETRY_INTERVAL_SECONDS", 5)


def ensure_directories() -> None:
    """Create the data/key directories if they do not already exist.

    Kept as an explicit function (rather than running on import) so that simply
    importing ``config`` never has filesystem side effects — useful for tests.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
