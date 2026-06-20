"""In-memory device registry mapping ``device_id`` -> public key (PEM).

A signature only proves anything if the server already knows the device's PUBLIC
key. So each device registers its public key once; afterwards the server looks it
up to verify that device's signed telemetry.

This prototype keeps the registry in memory and trusts the first registration of
a given ``device_id``. A production system would persist the registry and
authenticate registration (and support key rotation) - documented limitations.
"""

from __future__ import annotations

from app.crypto.signatures import load_public_key


class DeviceRegistry:
    """Holds the public key for every known device."""

    def __init__(self) -> None:
        self._public_keys: dict[str, str] = {}

    def register(self, device_id: str, public_key_pem: str) -> None:
        """Validate and store a device's public key.

        Raises ``ValueError`` if the PEM cannot be parsed as a public key, so
        bad keys are rejected at the door rather than failing later at verify
        time. (Duplicate detection is handled by the caller/endpoint.)
        """
        try:
            load_public_key(public_key_pem)
        except Exception as e:  # normalize any parse failure into ValueError
            raise ValueError(
                f"invalid public key for device '{device_id}': {e}"
            ) from e
        self._public_keys[device_id] = public_key_pem

    def get_public_key(self, device_id: str) -> str | None:
        """Return the device's public key PEM, or None if it is unknown."""
        return self._public_keys.get(device_id)

    def is_registered(self, device_id: str) -> bool:
        return device_id in self._public_keys

    def devices(self) -> list[str]:
        """List the IDs of all registered devices."""
        return list(self._public_keys)
