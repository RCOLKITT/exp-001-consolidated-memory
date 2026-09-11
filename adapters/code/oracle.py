"""Outcome oracle for the code adapter: flagged location vs. ground-truth patch.

    label(record) -> "bad"     flagged location overlaps a ground-truth hunk
                     "good"    flagged location overlaps nothing (false positive)
                     "unknown" no ground truth available for this instance

Record.content for this adapter is the defect-pattern text; the flagged
location is carried in Record.input_hash's companion metadata (see
`Flag`). Phase 2 wires `GroundTruth` from the corpus' gold patches.
"""
from __future__ import annotations

from dataclasses import dataclass

from memkernel.records import Record


@dataclass(frozen=True)
class Location:
    path: str
    start_line: int
    end_line: int
    symbol: str = ""     # v2: function/class qualname (or "<module>"); "" = file-level, matches any symbol

    def overlaps(self, other: "Location", slack: int = 0) -> bool:
        if self.symbol and other.symbol and self.symbol != other.symbol:
            return False      # both sides name a symbol: they must be the same one (closes the "<module>" loophole)
        return (
            self.path == other.path
            and self.start_line - slack <= other.end_line
            and other.start_line - slack <= self.end_line
        )

    @property
    def file_level(self) -> "Location":
        return Location(self.path, 1, 10**9)


@dataclass(frozen=True)
class Flag:
    instance_id: str
    location: Location
    pattern_text: str


class GroundTruth:
    """instance_id -> ground-truth hunk locations, parsed from gold patches.
    A `resolver` (v2) is called once per instance on first use to symbolise
    the hunks (function-level ground truth) and its result is memoised."""

    def __init__(self, hunks: dict[str, tuple[Location, ...]], resolver=None) -> None:
        self._hunks = hunks
        self._resolver = resolver
        self._resolved: dict[str, tuple[Location, ...]] = {}

    def locations(self, instance_id: str) -> tuple[Location, ...] | None:
        raw = self._hunks.get(instance_id)
        if raw is None or self._resolver is None:
            return raw
        if instance_id not in self._resolved:
            self._resolved[instance_id] = self._resolver(instance_id, raw)
        return self._resolved[instance_id]


class LocationOracle:
    def __init__(self, truth: GroundTruth, flags: dict[str, Flag], line_slack: int = 0) -> None:
        self.truth = truth
        self.flags = flags          # record.id -> Flag
        self.line_slack = line_slack

    def label(self, record: Record) -> str:
        flag = self.flags.get(record.id)
        if flag is None:
            return "unknown"
        gt = self.truth.locations(flag.instance_id)
        if gt is None:
            return "unknown"
        return "bad" if any(flag.location.overlaps(h, self.line_slack) for h in gt) else "good"
