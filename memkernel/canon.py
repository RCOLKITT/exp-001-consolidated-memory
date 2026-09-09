"""Canonical serialisation and content addressing.

Every hash in the kernel goes through `digest`. Canonical form is JSON with
sorted keys and no whitespace, so the same logical value always hashes the
same way regardless of construction order or process.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any


def _default(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    if isinstance(obj, tuple):
        return list(obj)
    if hasattr(obj, "to_canonical"):
        return obj.to_canonical()
    raise TypeError(f"not canonicalisable: {type(obj).__name__}")


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=_default)


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()
