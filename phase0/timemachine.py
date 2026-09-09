"""Time-machine dependency pinning (spec Phase 0, item 3; §8 dependency drift).

Rule: no package version released after the base commit's timestamp.

Two mechanisms, both driven by `cutoff_for(base_commit_date)`:
  1. `pip_env(cutoff)` — environment for `pypi-timemachine` (a local PyPI
     proxy that hides releases after a date). Install with
     `pip install pypi-timemachine`, run `pypi-timemachine <cutoff>` and point
     pip at it. This is the mechanism to use when building images.
  2. `check_freeze(freeze, release_dates, cutoff)` — after-the-fact audit of
     a `pip freeze` against a release-date table. Fails loudly on any package
     newer than the cutoff, and on any package whose date is unknown.

Note: Phase 0 localization needs only a git checkout at base_commit and no
dependency install, so pinning is exercised only when task images are built
(docs/DECISIONS.md D8).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable, Mapping

_FREEZE_RE = re.compile(r"^([A-Za-z0-9_.\-]+)==([^\s;]+)")


def cutoff_for(base_commit_time: datetime | date | int | float) -> date:
    """Cutoff date = the base commit's timestamp (UTC), inclusive."""
    if isinstance(base_commit_time, (int, float)):
        return datetime.fromtimestamp(base_commit_time, tz=timezone.utc).date()
    if isinstance(base_commit_time, datetime):
        return base_commit_time.astimezone(timezone.utc).date() if base_commit_time.tzinfo else base_commit_time.date()
    return base_commit_time


def pip_env(cutoff: date, port: int = 8040) -> dict[str, str]:
    """Env vars pointing pip at a pypi-timemachine proxy for `cutoff`."""
    return {
        "PIP_INDEX_URL": f"http://127.0.0.1:{port}/",
        "PIP_TRUSTED_HOST": "127.0.0.1",
        "TIMEMACHINE_CUTOFF": cutoff.isoformat(),
    }


def timemachine_command(cutoff: date, port: int = 8040) -> list[str]:
    # pypi-timemachine treats the cutoff as exclusive of later releases
    return ["pypi-timemachine", cutoff.isoformat(), "--port", str(port)]


@dataclass(frozen=True)
class Violation:
    package: str
    version: str
    released: date | None
    reason: str


def check_freeze(freeze_lines: Iterable[str], release_dates: Mapping[tuple[str, str], date], cutoff: date) -> list[Violation]:
    """Return every pinned package released after `cutoff` or of unknown date.

    `release_dates` maps (normalised_name, version) -> upload date.
    """
    out: list[Violation] = []
    for line in freeze_lines:
        m = _FREEZE_RE.match(line.strip())
        if not m:
            continue
        name, version = m.group(1).lower().replace("_", "-"), m.group(2)
        released = release_dates.get((name, version))
        if released is None:
            out.append(Violation(name, version, None, "unknown release date"))
        elif released > cutoff:
            out.append(Violation(name, version, released, f"released {released} > cutoff {cutoff}"))
    return out
