"""Deterministic (canonical) serialization for hashing and signing.

Why this module exists
----------------------
To hash or sign a piece of data we must first turn it into a fixed sequence of
bytes. The catch: the *same* logical data can be encoded many different ways.
These two Python dicts are equal...

    {"value": 21.5, "unit": "C"}
    {"unit": "C", "value": 21.5}

...but a naive ``json.dumps`` of each emits the keys in a different order, so the
resulting text differs, so the bytes differ, so the hash/signature differs. A
signature made over one ordering would FAIL to verify against the other — even
though nothing meaningful changed.

The fix is *canonicalization*: one logical input must always map to exactly one
byte string. We guarantee that with sorted keys, no insignificant whitespace,
and a fixed text encoding (UTF-8).
"""

from __future__ import annotations

import json
from typing import Any


def canonical_json(data: Any) -> str:
    """Serialize ``data`` to a canonical JSON *string*.

    Determinism comes from three settings:
      * ``sort_keys=True``        - object keys always appear in the same order
      * ``separators=(",", ":")`` - no spaces, so formatting cannot vary
      * ``ensure_ascii=False``    - text stays UTF-8 (encoded to bytes elsewhere)

    ``allow_nan=False`` rejects NaN/Infinity, which are not valid JSON and would
    otherwise produce non-portable output.
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def serialize(data: Any) -> bytes:
    """Serialize ``data`` to canonical UTF-8 *bytes* — the form we hash and sign.

    This is the single function the rest of the project calls whenever it needs
    the byte representation of an object, so hashing and signing always see
    byte-for-byte identical input.
    """
    return canonical_json(data).encode("utf-8")
