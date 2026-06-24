"""Unit tests for the sensor value generators."""

import pytest

from simulator.generators import (
    SensorGenerator,
    humidity_generator,
    pressure_generator,
    temperature_generator,
)

GENERATORS = {
    "temperature": (temperature_generator, "C", 15.0, 30.0),
    "humidity": (humidity_generator, "%", 30.0, 70.0),
    "pressure": (pressure_generator, "hPa", 990.0, 1030.0),
}


@pytest.mark.parametrize("name", list(GENERATORS))
def test_reading_has_correct_unit_and_shape(name):
    factory, unit, _lo, _hi = GENERATORS[name]
    reading = factory().next_reading()
    assert set(reading) == {"value", "unit"}
    assert reading["unit"] == unit
    assert isinstance(reading["value"], float)


@pytest.mark.parametrize("name", list(GENERATORS))
def test_values_stay_within_bounds_over_many_readings(name):
    factory, _unit, lo, hi = GENERATORS[name]
    gen = factory()
    for _ in range(500):
        value = gen.next_reading()["value"]
        assert lo <= value <= hi


def test_random_walk_moves_but_clamps():
    gen = SensorGenerator(unit="x", minimum=0.0, maximum=10.0, start=10.0, step=2.0)
    # Starting at the maximum, the value can never exceed it.
    for _ in range(50):
        assert gen.next_reading()["value"] <= 10.0
