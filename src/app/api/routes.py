"""API route handlers for the v1 endpoints.

Endpoints:
  POST /devices/register  - register a device's public key
  POST /telemetry         - verify a signed reading, mine it into a block, persist
  GET  /chain             - return the whole blockchain
  GET  /validate          - run validate_chain() and report valid/invalid

HTTP status codes are chosen to communicate *why* a request failed:
  400 bad public key · 401 bad signature · 404 unknown device · 409 duplicate
  · 422 malformed body (handled automatically by Pydantic).
"""

from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, HTTPException, status

from app.api import schemas
from app.api.dependencies import get_chain, get_lock, get_registry, get_store
from app.blockchain.chain import Blockchain
from app.blockchain.validation import validate_chain
from app.crypto.signatures import verify
from app.devices.registry import DeviceRegistry
from app.storage.base import BlockchainRepository

router = APIRouter()


@router.post(
    "/devices/register",
    response_model=schemas.DeviceRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_device(
    body: schemas.DeviceRegistrationRequest,
    registry: DeviceRegistry = Depends(get_registry),
) -> schemas.DeviceRegistrationResponse:
    """Register a device_id -> public_key mapping for later signature checks."""
    if registry.is_registered(body.device_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"device '{body.device_id}' is already registered",
        )
    try:
        registry.register(body.device_id, body.public_key)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return schemas.DeviceRegistrationResponse(
        device_id=body.device_id, message="device registered"
    )


@router.post(
    "/telemetry",
    response_model=schemas.TelemetryResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_telemetry(
    body: schemas.TelemetryRequest,
    chain: Blockchain = Depends(get_chain),
    store: BlockchainRepository = Depends(get_store),
    registry: DeviceRegistry = Depends(get_registry),
    lock: threading.Lock = Depends(get_lock),
) -> schemas.TelemetryResponse:
    """Verify a signed reading, mine it into a new block, and persist the chain."""
    public_key = registry.get_public_key(body.device_id)
    if public_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"device '{body.device_id}' is not registered",
        )

    if not verify(public_key, body.signable_bytes(), body.signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid signature: telemetry rejected",
        )

    transaction = body.model_dump()
    # Guard the read-modify-write of the chain so concurrent requests can't
    # interleave and corrupt it.
    with lock:
        block = chain.add_block([transaction])
        store.save(chain)

    return schemas.TelemetryResponse(
        message="telemetry accepted",
        block_index=block.index,
        block_hash=block.hash,
        chain_length=len(chain),
    )


@router.get("/chain", response_model=schemas.ChainResponse)
def get_full_chain(
    chain: Blockchain = Depends(get_chain),
) -> schemas.ChainResponse:
    """Return the entire blockchain."""
    data = chain.to_dict()
    return schemas.ChainResponse(
        difficulty=data["difficulty"], length=len(chain), blocks=data["blocks"]
    )


@router.get("/device/{device_id}", response_model=schemas.DeviceHistoryResponse)
def get_device_history(
    device_id: str,
    chain: Blockchain = Depends(get_chain),
    registry: DeviceRegistry = Depends(get_registry),
) -> schemas.DeviceHistoryResponse:
    """Return every telemetry transaction recorded for a single device.

    Walks every block in the chain and collects the transactions whose
    ``device_id`` matches. Returns 404 if the device was never registered.
    """
    if not registry.is_registered(device_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"device '{device_id}' is not registered",
        )

    records = [
        tx
        for block in chain.blocks
        for tx in block.transactions
        if isinstance(tx, dict) and tx.get("device_id") == device_id
    ]
    return schemas.DeviceHistoryResponse(
        device_id=device_id, total_records=len(records), records=records
    )


@router.get("/validate", response_model=schemas.ValidationResponse)
def validate(
    chain: Blockchain = Depends(get_chain),
) -> schemas.ValidationResponse:
    """Validate chain integrity and report the result."""
    result = validate_chain(chain)
    return schemas.ValidationResponse(
        valid=result.is_valid, reason=result.reason, block_index=result.block_index
    )
