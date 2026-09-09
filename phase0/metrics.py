"""Paired metrics (spec Phase 4 — always reported together).

localization rate  = tasks with >= 1 correct flag / tasks with ground truth
false-positive rate = flags with no ground-truth match / total flags

A flag is correct when its location overlaps a gold hunk (file-level flags
overlap any hunk in that file). Per-repo breakdown is mandatory (§8).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from adapters.code.oracle import Flag, GroundTruth


@dataclass(frozen=True)
class ArmMetrics:
    n_tasks: int
    n_localized: int
    n_flags: int
    n_false_positive: int
    per_repo: dict

    @property
    def localization_rate(self) -> float:
        return self.n_localized / self.n_tasks if self.n_tasks else 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.n_false_positive / self.n_flags if self.n_flags else 0.0

    def to_json(self) -> dict:
        d = asdict(self)
        d["localization_rate"] = round(self.localization_rate, 4)
        d["false_positive_rate"] = round(self.false_positive_rate, 4)
        return d


def score(flags_by_task: Mapping[str, Sequence[Flag]], truth: GroundTruth, repo_of: Mapping[str, str]) -> ArmMetrics:
    n_tasks = n_loc = n_flags = n_fp = 0
    per_repo: dict[str, dict[str, int]] = {}
    for iid, flags in flags_by_task.items():
        gt = truth.locations(iid)
        if gt is None:
            continue
        n_tasks += 1
        repo = repo_of.get(iid, "?")
        r = per_repo.setdefault(repo, {"n_tasks": 0, "n_localized": 0, "n_flags": 0, "n_false_positive": 0})
        r["n_tasks"] += 1
        hit_any = False
        for f in flags:
            n_flags += 1
            r["n_flags"] += 1
            if any(f.location.overlaps(h) for h in gt):
                hit_any = True
            else:
                n_fp += 1
                r["n_false_positive"] += 1
        if hit_any:
            n_loc += 1
            r["n_localized"] += 1
    for r in per_repo.values():
        r["localization_rate"] = round(r["n_localized"] / r["n_tasks"], 4) if r["n_tasks"] else 0.0
        r["false_positive_rate"] = round(r["n_false_positive"] / r["n_flags"], 4) if r["n_flags"] else 0.0
    return ArmMetrics(n_tasks, n_loc, n_flags, n_fp, per_repo)


def lift(treatment: ArmMetrics, control: ArmMetrics) -> dict:
    """Gate 4 numbers, in absolute points."""
    return {
        "localization_lift_pts": round(100 * (treatment.localization_rate - control.localization_rate), 2),
        "false_positive_rise_pts": round(100 * (treatment.false_positive_rate - control.false_positive_rate), 2),
    }


def dump(metrics: ArmMetrics, path) -> None:
    from pathlib import Path
    Path(path).write_text(json.dumps(metrics.to_json(), indent=1, sort_keys=True))
