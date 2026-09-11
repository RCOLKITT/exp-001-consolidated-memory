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
from phase0.functions import MODULE, FunctionIndexCache, enclosing_range

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


SOURCE_SUFFIXES = (".py",)


def is_source_path(path: str) -> bool:
    """v2: only Python source can carry a function-level target — the verifier's
    file list is `.py` only, so a hunk in CHANGES.rst or a JSON schema is
    unhittable by construction and is outside the function-level metric."""
    return path.endswith(SOURCE_SUFFIXES)


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


def symbolise_hunks(hunks, repo: str, commit: str, index: FunctionIndexCache) -> tuple[Location, ...]:
    """v2 function-level ground truth: each hunk becomes one Location per
    symbol it touches — the symbol's own line span with `symbol` set, or the
    hunk itself under `<module>` when no def/class encloses it (also when the
    file does not exist at base_commit, i.e. a pure addition)."""
    out: list[Location] = []
    for h in hunks:
        spans = index.spans(repo, commit, h.path)
        if not spans:
            loc = Location(h.path, h.start_line, h.end_line, MODULE)
            if loc not in out:
                out.append(loc)
            continue
        by_name = {s.qualname: s for s in spans}
        for name in enclosing_range(spans, h.start_line, h.end_line):
            sp = by_name.get(name)
            loc = Location(h.path, sp.start_line, sp.end_line, name) if sp else Location(h.path, h.start_line, h.end_line, MODULE)
            if loc not in out:
                out.append(loc)
    return tuple(out)


def function_ground_truth_from_tasks(tasks, index: FunctionIndexCache, exclude_tests: bool = True, source_only: bool = True) -> GroundTruth:
    """Lazy: hunks are symbolised on first lookup (needs the checkout, or the
    cache). With `source_only` (the v2 rule) non-Python hunks are dropped and a
    task left with no hunk resolves to None: outside the metric, not a miss."""
    base = ground_truth_from_tasks(tasks, exclude_tests)
    meta = {t.instance_id: (t.repo, t.base_commit) for t in tasks}

    def resolve(iid: str, hunks):
        repo, commit = meta[iid]
        hunks = tuple(h for h in hunks if not source_only or is_source_path(h.path))
        return symbolise_hunks(hunks, repo, commit, index) if hunks else None
    return GroundTruth(base._hunks, resolver=resolve)


def gold_symbols(task, index: FunctionIndexCache, exclude_tests: bool = True, source_only: bool = True) -> tuple[str, ...]:
    """`path::qualname` keys of the gold patch (function-level recurrence); same rule as the metric."""
    hunks = tuple(h for h in parse_patch(task.patch).hunks if not (exclude_tests and is_test_path(h.path)) and (not source_only or is_source_path(h.path)))
    return tuple(f"{l.path}::{l.symbol}" for l in symbolise_hunks(hunks, task.repo, task.base_commit, index))
