# API Reference

Base URL: `http://127.0.0.1:8000` · Base path: `/api/v1`

Interactive docs (Swagger UI) are served at `/docs` and the raw OpenAPI schema at
`/openapi.json` when the server is running.

All request and response bodies are JSON.

---

## POST /api/v1/devices/register

**Purpose:** Register a device's ECDSA public key so the server can later verify
that device's signed telemetry.

**Request body**

| Field | Type | Notes |
|-------|------|-------|
| `device_id` | string | Non-empty unique device identifier |
| `public_key` | string | PEM-encoded ECDSA public key |

```json
{
  "device_id": "temperature-001",
  "public_key": "-----BEGIN PUBLIC KEY-----\nMFkwEw...\n-----END PUBLIC KEY-----\n"
}
```

**Response — 201 Created**

```json
{ "device_id": "temperature-001", "message": "device registered" }
```

**Status codes**

| Code | Meaning |
|------|---------|
| 201 | Registered |
| 400 | `public_key` is not a valid PEM public key |
| 409 | `device_id` is already registered |
| 422 | Missing/invalid fields (Pydantic validation) |

**Example (curl)** — the `public_key` must be the full PEM with newlines escaped
as `\n` inside the JSON string:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{"device_id":"temperature-001","public_key":"-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n"}'
```

> In practice, keys are generated programmatically. See the Python snippet under
> `POST /telemetry` below, or just run the simulator, which registers devices for
> you.

---

## POST /api/v1/telemetry

**Purpose:** Submit a signed telemetry reading. The server verifies the
signature, mines a new block containing the reading, and persists the chain.

**Request body**

| Field | Type | Notes |
|-------|------|-------|
| `device_id` | string | Must be registered |
| `timestamp` | number | Unix seconds (float) |
| `payload` | object | `{ "value": number, "unit": string }` |
| `signature` | string | Hex ECDSA signature over the canonical bytes of `{device_id, timestamp, payload}` |

```json
{
  "device_id": "temperature-001",
  "timestamp": 1750000000.0,
  "payload": { "value": 22.5, "unit": "C" },
  "signature": "3045022100..."
}
```

**Response — 201 Created**

```json
{
  "message": "telemetry accepted",
  "block_index": 1,
  "block_hash": "00a1b2c3...",
  "chain_length": 2
}
```

**Status codes**

| Code | Meaning |
|------|---------|
| 201 | Accepted, block mined and persisted |
| 401 | Signature invalid (forged, wrong key, or tampered payload) |
| 404 | `device_id` is not registered |
| 422 | Missing/invalid fields (Pydantic validation) |

**Generating a valid request (Python).** A correct signature can't be written by
hand; produce one with the project's own helpers (run with `PYTHONPATH=src`,
server running):

```python
import time, requests
from app.crypto.signatures import generate_key_pair, sign
from app.crypto.serialization import serialize
from app.api.schemas import telemetry_signable_dict

BASE = "http://127.0.0.1:8000/api/v1"

private_pem, public_pem = generate_key_pair()
requests.post(f"{BASE}/devices/register",
              json={"device_id": "temperature-001", "public_key": public_pem})

ts = time.time()
payload = {"value": 22.5, "unit": "C"}
signature = sign(private_pem, serialize(telemetry_signable_dict("temperature-001", ts, payload)))

resp = requests.post(f"{BASE}/telemetry", json={
    "device_id": "temperature-001",
    "timestamp": ts,
    "payload": payload,
    "signature": signature,
})
print(resp.status_code, resp.json())
```

---

## GET /api/v1/chain

**Purpose:** Return the entire blockchain.

**Response — 200 OK**

```json
{
  "difficulty": 3,
  "length": 2,
  "blocks": [
    {
      "index": 0,
      "timestamp": 1750000000.0,
      "transactions": [],
      "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
      "nonce": 1234,
      "hash": "00f3a9..."
    },
    {
      "index": 1,
      "timestamp": 1750000005.0,
      "transactions": [
        {
          "device_id": "temperature-001",
          "timestamp": 1750000005.0,
          "payload": { "value": 22.5, "unit": "C" },
          "signature": "3045022100..."
        }
      ],
      "previous_hash": "00f3a9...",
      "nonce": 5821,
      "hash": "00b7c2..."
    }
  ]
}
```

**Status codes:** 200.

```bash
curl http://127.0.0.1:8000/api/v1/chain
```

---

## GET /api/v1/validate

**Purpose:** Validate chain integrity from the genesis block to the tip
(hash integrity, Proof-of-Work, `previous_hash` links, ordering, genesis).

**Response — 200 OK (valid)**

```json
{ "valid": true, "reason": "chain is valid", "block_index": null }
```

**Response — 200 OK (tampered)**

```json
{
  "valid": false,
  "reason": "block 1: stored hash does not match recomputed hash (block contents were modified)",
  "block_index": 1
}
```

**Status codes:** 200 (the body's `valid` field carries the result).

```bash
curl http://127.0.0.1:8000/api/v1/validate
```

> Note: this checks structural integrity, not each transaction's signature
> (signatures are verified at ingestion). See the security model in
> [architecture.md](architecture.md#security-model).

---

## GET /api/v1/device/{device_id}

**Purpose:** Return every telemetry transaction recorded for one device, across
all blocks.

**Response — 200 OK**

```json
{
  "device_id": "temperature-001",
  "total_records": 2,
  "records": [
    { "device_id": "temperature-001", "timestamp": 1750000005.0,
      "payload": { "value": 22.5, "unit": "C" }, "signature": "3045..." },
    { "device_id": "temperature-001", "timestamp": 1750000010.0,
      "payload": { "value": 22.6, "unit": "C" }, "signature": "3046..." }
  ]
}
```

A registered device with no readings yet returns `total_records: 0` and an empty
`records` list.

**Status codes**

| Code | Meaning |
|------|---------|
| 200 | OK (records may be empty) |
| 404 | `device_id` is not registered |

```bash
curl http://127.0.0.1:8000/api/v1/device/temperature-001
```
