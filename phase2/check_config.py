"""Verify a run's config against the registered one.

    python -m phase2.check_config docs/exp-run.v2.json results/experiment/10/config.json [more...]

Every key must be equal except the run-mechanics keys, which carry no
registered value: `repos` (must be one of the registered `shards`), `shard`,
`resume_run`, `secondary_repos`. Exit 1 on any other difference.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MECHANICS = {"repos", "shard", "resume_run", "secondary_repos", "merge_runs"}


def check(registered: dict, candidate: dict) -> list[str]:
    problems = []
    for k in sorted(set(registered) | set(candidate)):
        if k in MECHANICS:
            continue
        if registered.get(k) != candidate.get(k):
            problems.append(f"{k}: registered={registered.get(k)!r} run={candidate.get(k)!r}")
    if candidate.get("repos") != registered.get("repos"):
        shards = registered.get("shards", {})
        if candidate.get("repos") not in shards.values():
            problems.append("repos is neither the registered list nor one of its shards")
        elif candidate.get("shard") and shards.get(candidate["shard"]) != candidate["repos"]:
            problems.append(f"shard {candidate['shard']} does not match its registered repo list")
    return problems


def _main(argv):
    reg = json.loads(Path(argv[0]).read_text())
    bad = 0
    for f in argv[1:]:
        p = check(reg, json.loads(Path(f).read_text()))
        print(f"{f}: {'OK' if not p else 'MISMATCH'}" + ("".join(f"\n  - {x}" for x in p)))
        bad += bool(p)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
