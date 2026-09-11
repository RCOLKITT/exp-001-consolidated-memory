"""Fill the ⟦FILL⟧ values of docs/PREREGISTRATION-v2-DRAFT.md from the pre-runs,
under the rules fixed there (§4–5). No judgement calls live here; change the
rules in the draft first, then this file, never the other way round.

    python -m phase2.fill_v2 --recurrence results/phase0/24/recurrence.json --control results/phase0/24/control/metrics.json \
        --split results/experiment/5/split.json --negative-control sissbruecker/linkding --excluded streamlink/streamlink,pvlib/pvlib-python \
        [--tau 0.55 --tau-source results/...] --out docs/v2-fill.json

Rules:
  ceiling_repo   = eval_seen2(prefix = build size)  x (1 - p0_repo)           [pts]
  ceiling        = eval-pool-weighted mean of ceiling_repo
  p0             = eval-pool-weighted mean of p0_repo (function-level control, §5.2)
  MDE            = phase2.power.mde_at(p0, n = eval pool)                      [pts]
  kill number    = ceil(max(MDE, 0.5 x ceiling))                               [pts]
  feasible       = ceiling >= 1.5 x MDE
  gate3 floor    = 0.5 x build_repeat_share (per repo, §5.1) and >= 2 promoted
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from phase2.power import mde_at


def fill_prequential(preq: dict, control_per_repo: dict, repos: list[str], level: str = "function") -> dict:
    """Design A: pool and seen2 come from phase2.prequential (rolling window),
    p0 per repo from the function-level control run. Same rules as `fill`."""
    out = {}
    for repo in repos:
        d, c = preq.get("repos", {}).get(repo), control_per_repo.get(repo)
        if d is None or c is None:
            out[repo] = {"error": "missing prequential or control data"}
            continue
        lv = d[level]
        p0 = c["n_localized"] / c["n_tasks"] if c["n_tasks"] else 0.0
        out[repo] = {"chain": d["chain"], "n_eval": lv["n_scorable"], "p0": round(p0, 4), "eval_seen2": lv["seen2"] or 0.0,
                     "ceiling_pts": round(100 * (lv["seen2"] or 0.0) * (1 - p0), 1), "build_repeat_share": None, "gate3_discard_floor": None}
    return _aggregate(out)


def fill(recurrence: dict, control_per_repo: dict, split: dict, negative_control: str | None, excluded: list[str]) -> dict:
    """Registered-split design: seen2 at prefix = build size, from phase2.recurrence."""
    repos = {}
    for repo, build in split.items():
        if repo == negative_control or repo in excluded or repo.startswith("_"):
            continue
        d = recurrence.get(repo)
        c = control_per_repo.get(repo)
        if d is None or c is None:
            repos[repo] = {"error": "missing recurrence or control data"}
            continue
        row = next((r for r in d["rows"] if r["prefix"] == int(build)), None)
        if row is None or not row["n_eval"]:
            repos[repo] = {"error": f"no recurrence row at prefix {build}"}
            continue
        p0 = c["n_localized"] / c["n_tasks"] if c["n_tasks"] else 0.0
        seen2 = row["eval_file_seen2"] or 0.0
        repos[repo] = {"build": int(build), "n_eval": row["n_eval"], "p0": round(p0, 4), "eval_seen2": seen2,
                       "ceiling_pts": round(100 * seen2 * (1 - p0), 1),
                       "build_repeat_share": row.get("build_repeat_share"),
                       "gate3_discard_floor": round(0.5 * row["build_repeat_share"], 3) if row.get("build_repeat_share") is not None else None}
    return _aggregate(repos)


def _aggregate(repos: dict) -> dict:
    ok = {r: v for r, v in repos.items() if "error" not in v}
    pool = sum(v["n_eval"] for v in ok.values())
    p0 = sum(v["p0"] * v["n_eval"] for v in ok.values()) / pool if pool else 0.0
    ceiling = sum(v["ceiling_pts"] * v["n_eval"] for v in ok.values()) / pool if pool else 0.0
    mde = 100 * mde_at(p0, pool) if pool and 0 < p0 < 1 else float("nan")
    kill = math.ceil(max(mde, 0.5 * ceiling)) if not math.isnan(mde) else None
    return {"repos": repos, "eval_pool": pool, "p0": round(p0, 4), "ceiling_pts": round(ceiling, 1), "mde_pts": round(mde, 1) if not math.isnan(mde) else None,
            "kill_number_pts": kill, "feasible": (ceiling >= 1.5 * mde) if not math.isnan(mde) else None, "feasibility_rule": "ceiling >= 1.5 x MDE",
            "kill_rule": "ceil(max(MDE, 0.5 x ceiling))"}


def render(f: dict) -> str:
    out = ["| repo | build | eval | p0 (function) | seen2 | ceiling (pts) | repeat share | Gate 3 floor |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r, v in f["repos"].items():
        if "error" in v:
            out.append(f"| {r} | — | — | — | — | — | — | {v['error']} |")
        else:
            out.append(f"| {r} | {v.get('build', v.get('chain'))} | {v['n_eval']} | {v['p0']:.3f} | {v['eval_seen2']:.3f} | {v['ceiling_pts']} | {v['build_repeat_share']} | {v['gate3_discard_floor']} |")
    out.append("")
    out.append(f"eval pool {f['eval_pool']}; p0 {f['p0']}; ceiling {f['ceiling_pts']} pts; MDE {f['mde_pts']} pts; kill number {f['kill_number_pts']} pts ({f['kill_rule']}); feasible: {f['feasible']} ({f['feasibility_rule']})")
    return "\n".join(out) + "\n"


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recurrence"); ap.add_argument("--control", required=True); ap.add_argument("--split")
    ap.add_argument("--prequential", help="design A: phase2.prequential JSON instead of --recurrence/--split"); ap.add_argument("--repos", default="", help="design A: treatment repos")
    ap.add_argument("--negative-control"); ap.add_argument("--excluded", default=""); ap.add_argument("--out")
    a = ap.parse_args(argv)
    ctl = json.loads(Path(a.control).read_text())["per_repo"]
    if a.prequential:
        f = fill_prequential(json.loads(Path(a.prequential).read_text()), ctl, [r for r in a.repos.split(",") if r])
    else:
        f = fill(json.loads(Path(a.recurrence).read_text()), ctl, json.loads(Path(a.split).read_text()), a.negative_control, [x for x in a.excluded.split(",") if x])
    print(render(f))
    if a.out:
        Path(a.out).write_text(json.dumps(f, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
