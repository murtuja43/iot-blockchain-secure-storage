"""Unit tests for canonical (deterministic) serialization."""

import pytest

from app.crypto.serialization import canonical_json, serialize


def test_serialize_returns_bytes():
    assert isinstance(serialize({"a": 1}), bytes)


def test_keys_are_sorted():
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_key_order_does_not_change_output():
    # Same logical data, different insertion order -> identical bytes.
    a = {"device_id": "sensor-1", "value": 21.5, "unit": "C"}
    b = {"unit": "C", "value": 21.5, "device_id": "sensor-1"}
    assert serialize(a) == serialize(b)


def test_no_insignificant_whitespace():
    # Compact separators: no spaces after ':' or ','.
    assert canonical_json({"a": 1, "b": 2}) == '{"a":1,"b":2}'


def test_nested_objects_are_canonical():
    a = {"outer": {"y": 2, "x": 1}, "meta": {"b": 0, "a": 0}}
    b = {"meta": {"a": 0, "b": 0}, "outer": {"x": 1, "y": 2}}
    assert serialize(a) == serialize(b)


def test_list_order_is_preserved():
    # Lists are ordered data: their order is meaningful and must NOT be sorted.
    assert serialize({"l": [3, 2, 1]}) != serialize({"l": [1, 2, 3]})


def test_deterministic_across_calls():
    data = {"a": [1, 2, {"z": 9, "k": 0}], "b": "hi"}
    assert serialize(data) == serialize(data)


def test_different_data_differs():
    assert serialize({"v": 1}) != serialize({"v": 2})


def test_unicode_is_preserved_as_utf8():
    out = serialize({"unit": "°C"})  # "°C"
    assert "°C".encode("utf-8") in out


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nan_and_infinity_are_rejected(bad):
    with pytest.raises(ValueError):
        serialize({"value": bad})
