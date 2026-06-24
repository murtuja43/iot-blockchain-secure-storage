"""HTTP client for talking to the blockchain API.

This is the simulator's communication layer: it knows the endpoint URLs and how
to turn a non-2xx response (or a network failure) into a single, catchable
``APIError``. Keeping this separate from the device logic means the device never
touches ``requests`` directly - which also makes it trivial to test the device
with a fake client.
"""

from __future__ import annotations

from typing import Any

import requests

from app.config import API_BASE_URL, API_PREFIX


class APIError(Exception):
    """Raised when an API call fails (bad status code or network error)."""

    def __init__(self, status_code: int | None, message: str) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class BlockchainAPIClient:
    """Thin wrapper around the REST API used by simulated devices."""

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        prefix: str = API_PREFIX,
        session: Any | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.prefix = prefix
        self.session = session or requests.Session()
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{self.prefix}{path}"

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = self.session.post(
                self._url(path), json=payload, timeout=self.timeout
            )
        except requests.RequestException as e:  # connection refused, timeout, ...
            raise APIError(None, f"request to {path} failed: {e}") from e
        return self._handle(resp)

    def _get(self, path: str) -> dict[str, Any]:
        try:
            resp = self.session.get(self._url(path), timeout=self.timeout)
        except requests.RequestException as e:
            raise APIError(None, f"request to {path} failed: {e}") from e
        return self._handle(resp)

    @staticmethod
    def _handle(resp: Any) -> dict[str, Any]:
        if not 200 <= resp.status_code < 300:
            raise APIError(resp.status_code, resp.text)
        return resp.json()

    # --- endpoints --------------------------------------------------------

    def register_device(self, device_id: str, public_key_pem: str) -> dict[str, Any]:
        return self._post(
            "/devices/register",
            {"device_id": device_id, "public_key": public_key_pem},
        )

    def send_telemetry(self, transaction: dict[str, Any]) -> dict[str, Any]:
        return self._post("/telemetry", transaction)

    def get_chain(self) -> dict[str, Any]:
        return self._get("/chain")
