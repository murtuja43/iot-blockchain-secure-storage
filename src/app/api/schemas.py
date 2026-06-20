"""Pydantic request/response models for the REST API.

Pydantic gives us automatic request validation (wrong types / missing fields ->
a clean 422 error) and shapes the JSON responses + the Swagger docs at /docs.

The key contract here is ``telemetry_signable_dict``: it defines EXACTLY which
fields a device signs (everything except the signature itself). The device and
the server must agree on this structure, so it lives in one place that both the
API and - later - the simulator can use.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.crypto.serialization import serialize


def telemetry_signable_dict(
    device_id: str, timestamp: float, payload: dict[str, Any]
) -> dict[str, Any]:
    """The exact structure a device signs (telemetry minus the signature)."""
    return {"device_id": device_id, "timestamp": timestamp, "payload": payload}


# --- Requests -------------------------------------------------------------

class TelemetryPayload(BaseModel):
    value: float
    unit: str


class TelemetryRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    timestamp: float
    payload: TelemetryPayload
    signature: str = Field(..., min_length=1)

    def signable_bytes(self) -> bytes:
        """Canonical bytes the signature must be verified against."""
        return serialize(
            telemetry_signable_dict(
                self.device_id, self.timestamp, self.payload.model_dump()
            )
        )


class DeviceRegistrationRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    public_key: str = Field(..., min_length=1)


# --- Responses ------------------------------------------------------------

class DeviceRegistrationResponse(BaseModel):
    device_id: str
    message: str


class TelemetryResponse(BaseModel):
    message: str
    block_index: int
    block_hash: str
    chain_length: int


class BlockResponse(BaseModel):
    index: int
    timestamp: float
    transactions: list[dict[str, Any]]
    previous_hash: str
    nonce: int
    hash: str | None


class ChainResponse(BaseModel):
    difficulty: int
    length: int
    blocks: list[BlockResponse]


class ValidationResponse(BaseModel):
    valid: bool
    reason: str | None = None
    block_index: int | None = None
