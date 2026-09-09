"""Ground truth from gold patches: unified diff -> hunk locations.

Used by the code adapter's oracle (adapters/code/oracle.py) and by the
Phase 0 localization metric. Programmatic; no human reads findings.

Line ranges are in the PRE-image (base_commit) coordinate system, because
that is what a verifier looking at the unpatched repo can point at. A hunk
that only adds lines gets a zero-width range at its insertion point.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from adapters.code.oracle import GroundTruth, Location

_FILE_RE = re.compile(r"^diff --git a/(.+?) b/(.+)$")
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class PatchSummary:
    files: tuple[str, ...]
    hunks: tuple[Location, ...]


def parse_patch(patch: str) -> PatchSummary:
    files: list[str] = []
    hunks: list[Location] = []
    current: str | None = None
    for line in patch.splitlines():
        m = _FILE_RE.match(line)
        if m:
            current = m.group(2)
            if current not in files:
                files.append(current)
            continue
        if line.startswith("--- ") or line.startswith("+++ "):
            # `+++ b/path` is authoritative for renames; keep the diff --git name otherwise
            if line.startswith("+++ b/"):
                path = line[6:].strip()
                if current != path:
                    if current in files and current is not None:
                        files[files.index(current)] = path
                    current = path
            continue
        h = _HUNK_RE.match(line)
        if h and current is not None and not current.endswith("/dev/null"):
            start = int(h.group(1))
            length = int(h.group(2)) if h.group(2) is not None else 1
            end = start + max(length, 1) - 1
            hunks.append(Location(current, start, end))
    return PatchSummary(tuple(files), tuple(hunks))


def is_test_path(path: str) -> bool:
    p = path.lower()
    return "test" in p.split("/")[0] or "/tests/" in f"/{p}" or "/test/" in f"/{p}" or p.split("/")[-1].startswith("test_") or p.endswith("_test.py") or p.endswith("conftest.py")


def ground_truth_from_tasks(tasks, exclude_tests: bool = True) -> GroundTruth:
    """instance_id -> hunk locations of the gold patch (non-test files by default)."""
    table: dict[str, tuple[Location, ...]] = {}
    for t in tasks:
        summary = parse_patch(t.patch)
        hunks = tuple(h for h in summary.hunks if not (exclude_tests and is_test_path(h.path)))
        table[t.instance_id] = hunks
    return GroundTruth(table)


def gold_files(patch: str, exclude_tests: bool = True) -> tuple[str, ...]:
    return tuple(f for f in parse_patch(patch).files if not (exclude_tests and is_test_path(f)))
