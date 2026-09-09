"""Freshness gate — enforced at import, mechanically (spec Phase 0, item 2).

A task is admissible iff its creation date is strictly after the training
cutoff of EVERY model under evaluation. Tasks with no date are rejected: an
unknown date is not fresh.

    python -m phase0.freshness_gate tasks.jsonl models.json [--margin-days N]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Mapping


@dataclass(frozen=True)
class Verdict:
    instance_id: str
    created: date | None
    admitted: bool
    reason: str


def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def latest_cutoff(models: Mapping[str, object]) -> date:
    if not models:
        raise ValueError("no models given: the freshness gate cannot be applied")
    cutoffs = []
    for name, raw in models.items():
        d = _parse_date(raw)
        if d is None:
            raise ValueError(f"model {name!r} has an unparseable cutoff {raw!r}")
        cutoffs.append(d)
    return max(cutoffs)


def judge(task: Mapping[str, object], cutoff: date, margin_days: int = 0, date_key: str = "created_at") -> Verdict:
    iid = str(task.get("instance_id", "?"))
    created = _parse_date(task.get(date_key))
    if created is None:
        return Verdict(iid, None, False, f"missing or unparseable {date_key}")
    threshold = cutoff + timedelta(days=margin_days)
    if created <= threshold:
        return Verdict(iid, created, False, f"{created} <= cutoff {cutoff} (+{margin_days}d)")
    return Verdict(iid, created, True, "fresh")


def filter_tasks(tasks: Iterable[Mapping[str, object]], models: Mapping[str, object], margin_days: int = 0):
    cutoff = latest_cutoff(models)
    accepted, rejected = [], []
    for t in tasks:
        v = judge(t, cutoff, margin_days)
        (accepted if v.admitted else rejected).append((t, v))
    return accepted, rejected


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tasks_jsonl")
    ap.add_argument("models_json")
    ap.add_argument("--margin-days", type=int, default=0)
    ap.add_argument("--report", help="write per-task verdicts (for release) to this JSONL path")
    args = ap.parse_args(argv)
    with open(args.tasks_jsonl) as f:
        tasks = [json.loads(line) for line in f if line.strip()]
    with open(args.models_json) as f:
        models = json.load(f)
    accepted, rejected = filter_tasks(tasks, models, args.margin_days)
    if args.report:
        with open(args.report, "w") as f:
            for t, v in accepted + rejected:
                f.write(json.dumps({"instance_id": v.instance_id, "created": str(v.created), "admitted": v.admitted, "reason": v.reason}) + "\n")
    for t, _ in accepted:
        sys.stdout.write(json.dumps(t) + "\n")
    sys.stderr.write(f"freshness gate: {len(accepted)} admitted, {len(rejected)} rejected (cutoff {latest_cutoff(models)})\n")
    return 0 if accepted else 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
