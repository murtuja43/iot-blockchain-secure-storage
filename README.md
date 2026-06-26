# IoT Blockchain Secure Storage

> A prototype blockchain system for **secure, tamper-evident storage of IoT
> telemetry**. Simulated sensors cryptographically sign their readings; a REST
> API verifies each signature and appends the reading to a Proof-of-Work
> blockchain that is persisted to disk, so any later tampering with the stored
> history is detectable.

**Status:** prototype, feature-complete for its specification · **125 tests passing**.

---

## Overview

The system protects IoT telemetry with **two independent cryptographic
guarantees**:

1. **Authenticity & integrity in transit (per reading).** Each device owns an
   ECDSA key pair and signs every reading. The server verifies the signature
   against the device's registered public key, so a forged or altered reading is
   rejected at ingestion.
2. **Tamper-evidence of the stored history (whole chain).** Readings are stored
   in SHA-256 hash-linked blocks secured by Proof-of-Work. Editing any stored
   reading breaks the hash chain, which `validate_chain()` (and the
   `GET /validate` endpoint) detect and report.

These are different protections: a reading can be correctly signed yet sit in a
tampered chain, or vice-versa. The system checks both.

## Features

- ✅ IoT simulator with **three sensor types** (temperature, humidity, pressure)
- ✅ Automatic **ECDSA (P-256)** key generation, signing, and verification
- ✅ **Deterministic / canonical** serialization so hashes & signatures are stable
- ✅ Blockchain with genesis block, **adjustable-difficulty Proof-of-Work**
- ✅ Full-chain **validation & tamper detection** with human-readable reasons
- ✅ **JSON persistence** behind a swappable storage interface (atomic writes)
- ✅ **FastAPI** REST API with automatic Swagger docs at `/docs`
- ✅ In-memory **device registry** (public-key store)
- ✅ **Tamper-detection demo** script and cross-layer integration tests

## System Architecture

Clean, layered design — dependencies point inward only; the blockchain core
knows nothing about HTTP or files. See [docs/architecture.md](docs/architecture.md)
for diagrams and detail.

| Layer | Folder | Responsibility |
|-------|--------|----------------|
| Crypto | `src/app/crypto/` | SHA-256 hashing, ECDSA signatures, canonical serialization |
| Blockchain | `src/app/blockchain/` | Block & chain structures, Proof-of-Work, validation |
| Storage | `src/app/storage/` | Persist the chain (JSON) behind an abstract interface |
| Devices | `src/app/devices/` | In-memory device → public-key registry |
| API | `src/app/api/` | FastAPI app, routes, Pydantic schemas, DI |
| Simulator | `simulator/` | Signed telemetry from ≥3 simulated sensors (a client) |

## Technology Stack

- **Python 3.14** (developed/tested on 3.14.2; 3.11+ expected to work)
- **FastAPI + Uvicorn** — REST API with automatic OpenAPI/Swagger docs
- **Pydantic v2** — request/response validation
- **cryptography** (ECDSA P-256) + **hashlib** (SHA-256, standard library)
- **requests** — HTTP client used by the simulator
- **pytest** (+ httpx for the API TestClient) — testing

Exact versions are pinned with lower bounds in [requirements.txt](requirements.txt).
Tested with fastapi 0.137, uvicorn 0.49, pydantic 2.13, cryptography 49.0,
requests 2.34, pytest 9.1.

## Folder Structure

```
iot-blockchain-secure-storage/
├── src/app/
│   ├── config.py            # all tunable settings (env-overridable)
│   ├── crypto/              # serialization.py, hashing.py, signatures.py
│   ├── blockchain/          # block.py, chain.py, consensus.py, validation.py
│   ├── storage/             # base.py (interface), json_store.py
│   ├── devices/             # registry.py (public-key registry)
│   └── api/                 # main.py, routes.py, schemas.py, dependencies.py
├── simulator/               # device.py, generators.py, client.py, run_simulator.py
├── scripts/
│   └── demo_tamper_detection.py
├── tests/                   # crypto/ blockchain/ storage/ api/ simulator/ integration/
├── docs/                    # architecture.md, api.md, testing.md, demo.md
├── data/                    # chain.json at runtime (git-ignored)
├── requirements.txt
├── pyproject.toml           # pytest config
└── README.md
```

## Installation

```bash
git clone <your-repo-url>
cd iot-blockchain-secure-storage

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

All settings live in [src/app/config.py](src/app/config.py) and can be overridden
with environment variables:

| Variable | Default | Meaning |
|----------|---------|---------|
| `POW_DIFFICULTY` | `3` | Number of leading zero hex digits a block hash must have |
| `API_HOST` | `127.0.0.1` | API bind host |
| `API_PORT` | `8000` | API port |
| `API_BASE_URL` | `http://127.0.0.1:8000` | Base URL the simulator targets |
| `TELEMETRY_INTERVAL_SECONDS` | `5` | Default simulator send interval |

```bash
export POW_DIFFICULTY=4
export API_PORT=8080
```

## Running the API

```bash
uvicorn app.api.main:app --app-dir src --host 127.0.0.1 --port 8000
```

Then open the interactive Swagger docs: **http://127.0.0.1:8000/docs**

On startup the app loads `data/chain.json` if present, or creates a new chain
(with a genesis block) on first run.

## Running the IoT Simulator

Start the API first (above), then in a second terminal:

```bash
PYTHONPATH=src python -m simulator.run_simulator --interval 5
# or:  python simulator/run_simulator.py --interval 5
```

Options: `--interval <seconds>`, `--url <api-base-url>`, `--duration <seconds>`
(0 = run until Ctrl+C). Stop with **Ctrl+C** for a graceful shutdown.

> If port 8000 is already in use, run uvicorn on another port and point the
> simulator at it, e.g. `--url http://127.0.0.1:8077`.

## Running the Tamper-Detection Demo

```bash
python scripts/demo_tamper_detection.py
# or against an existing chain (works on a safe COPY, never modifies it):
python scripts/demo_tamper_detection.py --file data/chain.json
```

The demo seeds (or loads) a chain, validates it, edits a stored telemetry value
directly in the JSON file, reloads, and shows validation now fails — see
[docs/demo.md](docs/demo.md).

## Running Tests

```bash
pytest                 # full suite (125 tests)
pytest tests/api/ -v   # one area
```

Pytest is configured in [pyproject.toml](pyproject.toml). See
[docs/testing.md](docs/testing.md) for the breakdown.

## API Overview

Base path: `/api/v1`. Full reference with request/response shapes and examples
in [docs/api.md](docs/api.md).

| Method | Path | Description |
|--------|------|-------------|
| POST | `/devices/register` | Register a device's public key |
| POST | `/telemetry` | Submit a signed reading (verified, mined, persisted) |
| GET | `/chain` | Return the full blockchain |
| GET | `/validate` | Validate chain integrity (valid/invalid + reason) |
| GET | `/device/{device_id}` | Telemetry history for one device |

## Security Features

- **ECDSA P-256 signatures** verified at ingestion — invalid/forged/altered
  readings are rejected with `401`.
- **Canonical serialization** ensures device and server hash/verify identical
  bytes regardless of JSON key order.
- **SHA-256 hash chaining + Proof-of-Work** make the stored history
  tamper-evident: editing any block breaks every link after it.
- **Atomic file writes** (temp file + `os.replace`) prevent half-written,
  corrupt chain files.
- **Graceful failure** on bad input: malformed bodies → `422`, unknown device →
  `404`, bad key → `400`, corrupted/invalid storage → clear `StorageError`.

See the security model in [docs/architecture.md](docs/architecture.md#security-model)
for what is and isn't protected.

## Example Workflow

1. Start the API (`uvicorn ...`).
2. A device registers its public key: `POST /devices/register`.
3. The device signs a reading and submits it: `POST /telemetry` → the server
   verifies the signature, mines a block, and persists the chain.
4. Anyone inspects the ledger: `GET /chain`, a device's history:
   `GET /device/{id}`, or integrity: `GET /validate`.
5. The simulator automates steps 2–3 for three sensors concurrently.

A runnable end-to-end walkthrough is in [docs/demo.md](docs/demo.md).

## Future Improvements

This is a learning-focused prototype. To move toward production:

- **Persist the device registry** (currently in-memory; lost on restart) and
  authenticate device registration; support key rotation.
- **Re-verify transaction signatures during `validate_chain`** (it currently
  checks hashes, PoW, and links — signatures are verified only at ingestion).
- **Transaction batching** — `MEMPOOL_BLOCK_SIZE` exists in config but each
  reading currently becomes its own block; wire up a mempool to batch.
- **Concurrency/scale** — single-process with a write lock; a real deployment
  needs a proper datastore (e.g. SQLite, behind the existing storage interface)
  and/or multi-node consensus.
- **Transport security** (TLS), rate limiting, and authentication on read APIs.
- **Encrypted private keys at rest** for simulated/real devices.

## License

No license has been specified yet. Add a `LICENSE` file (e.g. MIT) before any
public or third-party use.
