# IoT Blockchain Secure Storage

> A prototype blockchain system for **secure, tamper-evident storage of IoT
> telemetry**. Simulated sensors cryptographically sign their readings; a REST
> API verifies the signatures and stores the data in a Proof-of-Work
> blockchain, so any later tampering with the history is detectable.

**Status:** 🚧 In development — **Phase 0 (project scaffolding) complete.**

> This README is a skeleton. Sections marked _TODO_ are filled in during the
> phase noted next to them. Full documentation lands in Phase 8.

---

## Overview
_TODO (Phase 8): high-level description, goals, and the two security guarantees
(per-reading signatures vs. whole-chain immutability)._

## Architecture
The system is built in clean, independently testable layers. Dependencies point
inward only — the blockchain core knows nothing about HTTP or files.

| Layer | Folder | Responsibility | Phase |
|-------|--------|----------------|-------|
| Crypto | `src/app/crypto/` | SHA-256 hashing + ECDSA signatures | 1 |
| Blockchain | `src/app/blockchain/` | Block/chain structures, PoW, validation | 2–3 |
| Storage | `src/app/storage/` | Persist the chain (JSON, behind an interface) | 4 |
| API | `src/app/api/` | REST endpoints (FastAPI) | 5 |
| Devices | `src/app/devices/` | Device registry / public-key store | 5 |
| Simulator | `simulator/` | Signed telemetry from ≥3 simulated sensors | 6 |

_TODO (Phase 8): architecture diagram._

## Tech Stack
- **Python 3.14** (developed on; 3.11+ should work)
- **FastAPI + Uvicorn** — REST API with automatic Swagger docs
- **Pydantic** — request/response validation
- **cryptography** (ECDSA signatures) + **hashlib** (SHA-256)
- **pytest** — testing

## Project Structure
```
iot-blockchain-secure-storage/
├── src/app/
│   ├── config.py            # all tunable settings in one place
│   ├── crypto/              # hashing + signatures            (Phase 1)
│   ├── blockchain/          # block, chain, PoW, validation   (Phase 2–3)
│   ├── storage/             # JSON persistence behind interface (Phase 4)
│   ├── api/                 # FastAPI app + routes            (Phase 5)
│   └── devices/             # device registry / keystore      (Phase 5)
├── simulator/               # simulated IoT sensors           (Phase 6)
├── tests/                   # pytest suite
├── scripts/                 # demo scripts (e.g. tamper demo) (Phase 7)
├── data/                    # chain.json + device keys (git-ignored)
├── docs/                    # extra documentation
├── requirements.txt
├── .gitignore
└── README.md
```

## Getting Started
### Prerequisites
- Python 3.11+ (developed on 3.14)
- git

### Installation
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration
All settings live in [`src/app/config.py`](src/app/config.py) and can be
overridden with environment variables, e.g.:
```bash
export POW_DIFFICULTY=4
export API_PORT=8080
```

## Running the System
_TODO (Phase 5/6): how to start the API server and run the IoT simulator._

## API Endpoints
| Method | Path | Description | Phase |
|--------|------|-------------|-------|
| POST | `/api/v1/telemetry` | Receive a signed reading from a device | 5 |
| GET | `/api/v1/chain` | View the entire blockchain | 5 |
| GET | `/api/v1/validate` | Check chain integrity (valid/invalid) | 5 |
| GET | `/api/v1/device/{id}` | Telemetry history for one device | 5 |

_TODO (Phase 8): sample requests (curl) for each endpoint._

## Testing
```bash
pytest
```
_(Tests are added from Phase 1 onward.)_

## Roadmap
- **Phase 0** — Project scaffolding ✅
- **Phase 1** — Cryptographic foundation (SHA-256 + ECDSA)
- **Phase 2** — Block, chain & Proof-of-Work
- **Phase 3** — Chain validation & tamper detection
- **Phase 4** — JSON persistence layer
- **Phase 5** — REST API + device registry
- **Phase 6** — IoT simulator (≥3 sensors)
- **Phase 7** — Tamper-detection demo & integration tests
- **Phase 8** — Documentation & polish

## Security Notes
_TODO (Phase 7): signature verification, tamper detection, and known
limitations of this prototype._

## License
_TODO_
