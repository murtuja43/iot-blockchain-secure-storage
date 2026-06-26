# Testing

The project has **125 passing tests** covering every layer from cryptographic
primitives up to a full end-to-end pipeline.

## Running the tests

```bash
source .venv/bin/activate
pytest                      # full suite (125)
pytest tests/api/ -v        # one area, verbose
pytest -k "tamper"          # filter by keyword
```

Configuration lives in [pyproject.toml](../pyproject.toml): `src/` and the repo
root are placed on the import path, and `tests/` is the test root.

## Test breakdown

| Area | Path | Count | What it covers |
|------|------|-------|----------------|
| Crypto | `tests/crypto/` | 30 | Canonical serialization, SHA-256 (known vectors, avalanche), ECDSA sign/verify, tamper/wrong-key/malformed-signature handling, PEM round-trip |
| Blockchain | `tests/blockchain/` | 36 | Block hashing, Proof-of-Work, chain genesis/append/linking, full validation & tamper detection |
| Storage | `tests/storage/` | 15 | Save/load round-trip, restart, abstract-class enforcement, missing-file / corrupted-JSON / invalid-structure errors, tamper-after-load |
| API | `tests/api/` | 19 | All 5 endpoints: registration, signed ingestion, signature failures, persistence, chain/validate/device |
| Simulator | `tests/simulator/` | 21 | Generators (bounds/units), API client (mocked), device signing/registration, workflow incl. real end-to-end run |
| Integration | `tests/integration/` | 4 | Cross-layer pipeline, storage reload→validation, tamper detection, demo script |
| **Total** | | **125** | |

## Unit tests

Each module is tested in isolation:

- **Serialization** — key-order independence, compact output, NaN/Infinity
  rejection, UTF-8 preservation.
- **Hashing** — official SHA-256 test vectors, fixed digest length, avalanche
  effect, object-hash determinism.
- **Signatures** — sign→verify round-trips, and crucially the *failure* paths:
  tampered data, wrong public key, flipped/malformed signatures all return
  `False` (never raise).
- **Block / consensus / chain** — content-derived hashing, nonce mining at
  several difficulties, sequential indices, `previous_hash` linkage.

## Integration tests

`tests/integration/` exercises multiple layers together:

- **`test_pipeline.py`** — drives the **real simulator client** against the
  **real API** (via FastAPI's `TestClient`) backed by a temp-file store, then
  asserts the data reached disk, reloads it after a simulated restart and
  validates it, and finally tampers the stored file and confirms detection
  (via both `validate_chain()` and the `/validate` endpoint).
- **`test_demo_script.py`** — runs the tamper-detection demo's `run_demo()` and
  asserts it reports valid-before / invalid-after with the correct block index.

## Simulator tests

`tests/simulator/` includes a genuine end-to-end test
(`test_end_to_end_simulator_against_real_api`) where three devices register and
stream signed telemetry into a real chain, after which the chain validates and
per-device history is queryable. The API client tests use mocked HTTP sessions so
they need no running server.

## Tamper-detection tests

Tampering is verified at several levels:

- **Unit** (`tests/blockchain/test_validation.py`): tampered transaction,
  tampered block hash, broken `previous_hash`, invalid Proof-of-Work, genesis
  corruption, early-block cascade.
- **Storage** (`tests/storage/test_json_store.py`): editing the JSON file on
  disk is detected after reload.
- **Integration** (`tests/integration/`): tampering after a full pipeline run is
  detected by both `validate_chain()` and `GET /validate`.

## Notes

- A harmless `StarletteDeprecationWarning` may appear from the FastAPI
  `TestClient` (an internal httpx note); it does not affect results.
- Tests use temporary files/stores and never write to the real `data/chain.json`.
