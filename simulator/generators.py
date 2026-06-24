"""Realistic telemetry value generators for simulated sensors.

Real sensors don't jump randomly between extremes - readings drift smoothly. We
model that with a *bounded random walk*: each reading nudges the previous value
by a small random step and clamps it to a sensible range. The result looks like
plausible sensor data rather than noise.
"""

from __future__ import annotations

import random
from typing import Any


class SensorGenerator:
    """Produces a smoothly-varying stream of readings for one physical quantity."""

    def __init__(
        self,
        unit: str,
        minimum: float,
        maximum: float,
        start: float | None = None,
        step: float = 1.0,
        precision: int = 2,
    ) -> None:
        self.unit = unit
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.precision = precision
        # Start in the middle of the range unless told otherwise.
        self.value = start if start is not None else (minimum + maximum) / 2

    def next_reading(self) -> dict[str, Any]:
        """Advance the random walk and return a ``{"value", "unit"}`` payload."""
        self.value += random.uniform(-self.step, self.step)
        self.value = max(self.minimum, min(self.maximum, self.value))  # clamp
        return {"value": round(self.value, self.precision), "unit": self.unit}


def temperature_generator() -> SensorGenerator:
    """Indoor temperature in degrees Celsius (~15-30 C, around 22 C)."""
    return SensorGenerator(unit="C", minimum=15.0, maximum=30.0, start=22.0, step=0.5)


def humidity_generator() -> SensorGenerator:
    """Relative humidity in percent (~30-70 %, around 50 %)."""
    return SensorGenerator(unit="%", minimum=30.0, maximum=70.0, start=50.0, step=1.5)


def pressure_generator() -> SensorGenerator:
    """Atmospheric pressure in hectopascals (~990-1030 hPa, around 1013 hPa)."""
    return SensorGenerator(
        unit="hPa", minimum=990.0, maximum=1030.0, start=1013.0, step=0.7
    )
