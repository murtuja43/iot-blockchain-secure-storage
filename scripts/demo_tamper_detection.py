"""Tamper-detection demonstration.

Shows, end to end, that the blockchain is *tamper-evident*:

  1. Load a chain and confirm it validates.
  2. Edit a stored telemetry value directly in the JSON file (as an attacker
     with disk access would) - without re-mining.
  3. Reload the file and run validate_chain() again -> it is now INVALID, and
     reports exactly which block was changed.

Run it:
    python scripts/demo_tamper_detection.py                 # seeds a demo chain
    python scripts/demo_tamper_detection.py --file data/chain.json

SAFETY: the demo always works on a temporary COPY. Your original chain file is
read but never modified.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `app` (under src/) importable whether run as a script or a module.
_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import argparse  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402

from app.api.schemas import telemetry_signable_dict  # noqa: E402
from app.blockchain.chain import Blockchain  # noqa: E402
from app.blockchain.validation import validate_chain  # noqa: E402
from app.crypto.serialization import serialize  # noqa: E402
from app.crypto.signatures import generate_key_pair, sign  # noqa: E402
from app.storage.json_store import JsonBlockchainStore  # noqa: E402

SEP = "=" * 70


def _make_reading(device_id: str, private_pem: str, value: float, unit: str, ts: float) -> dict:
    """Build a properly signed telemetry transaction (as the API would store)."""
    payload = {"value": value, "unit": unit}
    signature = sign(
        private_pem, serialize(telemetry_signable_dict(device_id, ts, payload))
    )
    return {
        "device_id": device_id,
        "timestamp": ts,
        "payload": payload,
        "signature": signature,
    }


def seed_demo_chain(store: JsonBlockchainStore, difficulty: int = 2) -> Blockchain:
    """Create and save a small demo chain with three signed readings."""
    chain = Blockchain(difficulty=difficulty)
    private_pem, _ = generate_key_pair()
    readings = [
        ("temperature-001", 22.5, "C"),
        ("humidity-001", 48.0, "%"),
        ("pressure-001", 1013.2, "hPa"),
    ]
    for i, (device_id, value, unit) in enumerate(readings):
        chain.add_block([_make_reading(device_id, private_pem, value, unit, 1000.0 + i)])
    store.save(chain)
    return chain


def tamper_first_telemetry(path: Path, new_value: float) -> tuple[int, float, float]:
    """Edit the first telemetry value directly in the JSON file on disk.

    Returns ``(block_index, old_value, new_value)``.
    """
    data = json.loads(path.read_text())
    block = data["blocks"][1]  # block 0 is genesis; block 1 holds the first reading
    tx = block["transactions"][0]
    old_value = tx["payload"]["value"]
    tx["payload"]["value"] = new_value
    path.write_text(json.dumps(data, indent=2))
    return block["index"], old_value, new_value


def run_demo(source_path: str | None = None, difficulty: int = 2, new_value: float = 999.99) -> dict:
    """Run the full demonstration and return a summary dict (also prints it)."""
    work_dir = Path(tempfile.mkdtemp(prefix="tamper_demo_"))
    work_path = work_dir / "chain.json"
    store = JsonBlockchainStore(work_path)

    print(SEP)
    print(" TAMPER-DETECTION DEMONSTRATION")
    print(SEP)

    # 1. Get a chain to work with - always a safe copy.
    if source_path and Path(source_path).exists():
        original = JsonBlockchainStore(source_path).load()
        store.save(original)
        print(f"[1] Loaded existing chain from: {source_path}")
    else:
        seed_demo_chain(store, difficulty)
        if source_path:
            print(f"[1] '{source_path}' not found - created a fresh demo chain instead.")
        else:
            print("[1] No --file given - created a fresh demo chain.")
    print(f"    Working on a safe copy at: {work_path}")
    print()

    # 2. Validate the untampered chain.
    chain = store.load()
    before = validate_chain(chain)
    print(f"[2] Verifying the chain ({len(chain)} blocks: genesis + {len(chain) - 1} telemetry)...")
    print(f"    validate_chain() -> {'VALID' if before.is_valid else 'INVALID'}  ({before.reason})")
    print()

    # 3. Tamper a stored value directly on disk (no re-mining).
    block_index, old_value, new_value = tamper_first_telemetry(work_path, new_value)
    print("[3] Tampering with stored data on disk (editing the JSON, not re-mining)...")
    print(f"    block {block_index}: payload.value  {old_value}  ->  {new_value}")
    print()

    # 4. Reload and re-validate.
    reloaded = store.load()
    after = validate_chain(reloaded)
    print("[4] Reloading the tampered file and re-validating...")
    print(f"    validate_chain() -> {'VALID' if after.is_valid else 'INVALID'}")
    print(f"    reason: {after.reason}")
    print(f"    offending block index: {after.block_index}")
    print()

    detected = before.is_valid and not after.is_valid
    print(SEP)
    print(f" RESULT: tampering was {'DETECTED' if detected else 'NOT detected (unexpected!)'}.")
    print(SEP)

    return {
        "valid_before": before.is_valid,
        "valid_after": after.is_valid,
        "reason": after.reason,
        "block_index": after.block_index,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Demonstrate blockchain tamper detection (works on a safe copy)."
    )
    parser.add_argument(
        "--file", default=None,
        help="path to an existing chain.json (the original is never modified)",
    )
    parser.add_argument("--difficulty", type=int, default=2)
    args = parser.parse_args(argv)
    run_demo(source_path=args.file, difficulty=args.difficulty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
