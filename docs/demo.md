# Demonstration Guide

A complete, runnable walkthrough: start the API, stream signed telemetry from the
simulator, inspect the chain, and prove tamper detection works.

Prerequisite: install dependencies first (see the README) and activate the venv:

```bash
source .venv/bin/activate
```

---

## 1. Start the API

```bash
uvicorn app.api.main:app --app-dir src --host 127.0.0.1 --port 8000
```

Open the interactive docs at **http://127.0.0.1:8000/docs**. On first run the app
creates a new chain (`data/chain.json`) with a genesis block.

> If port 8000 is busy, pick another (e.g. `--port 8077`) and pass the same URL
> to the simulator with `--url` in the next step.

Check it's alive (in a second terminal):

```bash
curl http://127.0.0.1:8000/api/v1/chain
curl http://127.0.0.1:8000/api/v1/validate
# -> {"valid":true,"reason":"chain is valid","block_index":null}
```

## 2. Run the IoT simulator

In the second terminal:

```bash
PYTHONPATH=src python -m simulator.run_simulator --interval 1 --duration 8
```

This creates three devices (temperature, humidity, pressure), registers their
public keys, and streams signed readings. Real output looks like:

```
Starting simulator -> http://127.0.0.1:8000 (interval=1.0s)
[register] temperature-001: ok
[register] humidity-001: ok
[register] pressure-001: ok
[pressure-001] 1012.96 hPa -> block 1 (chain length 2)
[temperature-001] 22.2 C   -> block 2 (chain length 3)
[humidity-001] 51.02 %     -> block 3 (chain length 4)
[pressure-001] 1012.5 hPa  -> block 4 (chain length 5)
...
All devices stopped. Goodbye.
```

Omit `--duration` to run until you press **Ctrl+C** (graceful shutdown).

## 3. Inspect the ledger

```bash
# Whole chain
curl http://127.0.0.1:8000/api/v1/chain

# History for one device
curl http://127.0.0.1:8000/api/v1/device/temperature-001

# Integrity check
curl http://127.0.0.1:8000/api/v1/validate
# -> {"valid":true,"reason":"chain is valid","block_index":null}
```

You can also explore and call every endpoint from the Swagger UI at `/docs`.

## 4. Tamper-detection demo

The demo script is self-contained — it does **not** need the server running and
operates on a safe temporary copy (it never modifies your real chain):

```bash
python scripts/demo_tamper_detection.py
```

Real output:

```
======================================================================
 TAMPER-DETECTION DEMONSTRATION
======================================================================
[1] No --file given - created a fresh demo chain.
    Working on a safe copy at: /var/folders/.../tamper_demo_xxxx/chain.json

[2] Verifying the chain (4 blocks: genesis + 3 telemetry)...
    validate_chain() -> VALID  (chain is valid)

[3] Tampering with stored data on disk (editing the JSON, not re-mining)...
    block 1: payload.value  22.5  ->  999.99

[4] Reloading the tampered file and re-validating...
    validate_chain() -> INVALID
    reason: block 1: stored hash does not match recomputed hash (block contents were modified)
    offending block index: 1

======================================================================
 RESULT: tampering was DETECTED.
======================================================================
```

To run it against a chain produced by the live server (safely, on a copy):

```bash
python scripts/demo_tamper_detection.py --file data/chain.json
```

## 5. Tamper detection by hand (optional)

Because the chain is stored as readable JSON, you can prove detection yourself:

1. Stop the server.
2. Open `data/chain.json` and change a `payload.value` in any non-genesis block.
3. Restart the server and call `GET /api/v1/validate`:

```bash
curl http://127.0.0.1:8000/api/v1/validate
# -> {"valid":false,"reason":"block N: stored hash does not match recomputed hash ...","block_index":N}
```

The edited block's recomputed hash no longer matches its stored hash, so the
chain is reported invalid — with the offending block index.

## 6. Run the tests

```bash
pytest          # 125 passing
```

See [testing.md](testing.md) for the full breakdown.
