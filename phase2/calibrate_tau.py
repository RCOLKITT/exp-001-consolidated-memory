"""τ calibration (v2 draft §5.3, design A): from rolling runs on the
calibration repos — repos that are neither treatment nor negative control —
collect every (retrieval cosine, memory names a gold symbol) pair seen by
the ungated arm and apply the registered rule:

  τ = the lowest threshold θ in {0.00, 0.05, ..., 0.95} at which
      precision(θ) = P(memory names a gold symbol | cosine >= θ) first reaches 0.5;
      if it never does, τ = the 90th percentile of the non-matching cosines,
      rounded to 0.05.

    python -m phase2.calibrate_tau --rolling-dir results/experiment/N/rolling --arm ungated --out tau.json

Reads only arms.json (scores, memory_locations, gold) — no corpus, no model.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def pairs_from_arms(a: dict, arm: str) -> list[tuple[float, bool]]:
    locs, gold = a.get("memory_locations", {}), a.get("gold", {})
    out = []
    for iid, scores in a["arms"][arm].get("scores", {}).items():
        g = set(gold.get(iid, []))
        if not g:
            continue
        for mid, cos in scores.items():
            out.append((float(cos), locs.get(mid) in g))
    return out


def calibrate(pairs: list[tuple[float, bool]], target: float = 0.5, step: float = 0.05) -> dict:
    grid = [round(i * step, 2) for i in range(int(round(1 / step)))]
    curve = []
    for th in grid:
        sel = [m for c, m in pairs if c >= th]
        curve.append({"theta": th, "n": len(sel), "precision": round(sum(sel) / len(sel), 4) if sel else None})
    tau, rule = None, "precision >= 0.5"
    for row in curve:
        if row["precision"] is not None and row["precision"] >= target:
            tau = row["theta"]
            break
    if tau is None:
        neg = sorted(c for c, m in pairs if not m)
        if neg:
            q = neg[min(len(neg) - 1, int(0.9 * len(neg)))]
            tau = round(round(q / step) * step, 2)
        rule = "90th percentile of non-matching cosines (precision never reached 0.5)"
    return {"tau": tau, "rule": rule, "n_pairs": len(pairs), "n_match": sum(1 for _, m in pairs if m), "curve": curve}


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rolling-dir", required=True); ap.add_argument("--arm", default="ungated"); ap.add_argument("--out")
    a = ap.parse_args(argv)
    pairs, repos = [], []
    for f in sorted(Path(a.rolling_dir).glob("*.arms.json")) or sorted(Path(a.rolling_dir).glob("*/arms.json")):
        d = json.loads(f.read_text())
        if a.arm not in d.get("arms", {}):
            continue
        pr = pairs_from_arms(d, a.arm); pairs += pr; repos.append({"file": f.name if f.name != "arms.json" else f.parent.name, "n_pairs": len(pr)})
    res = calibrate(pairs); res["repos"] = repos; res["arm"] = a.arm
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    sys.stdout.write(json.dumps({k: res[k] for k in ("tau", "rule", "n_pairs", "n_match", "repos")}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
