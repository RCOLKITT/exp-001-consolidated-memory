"""Paired task-level analysis of a Phase 4 evaluation (post-hoc, descriptive).

    python -m phase4.paired --eval-dir results/experiment/6/eval [--tasks corpus/tasks.jsonl] \
        [--negative-control owner/name] [--secondary-repos a/b,c/d] [--treatment-arm treatment] --out results/experiment/6/paired

Reads the per-repo ``arms.json`` files written by ``phase4.evaluate``. Files
written by v2 carry per-task hits under ``arms[<name>].hits`` and need no
corpus; older files (v1) need ``--tasks`` so file-level hits can be
recomputed from gold files. Either way the analysis reports, per arm pair,
and reports what the aggregate ``gate4.json`` cannot: discordant pairs
(control-only hit vs treatment-only hit), an exact McNemar p-value, a paired
confidence interval on the lift, retrieval coverage and how often the
treatment's flags actually differed from control. A registered secondary
subset (``--secondary-repos``) is reported alongside, never instead of, the
primary. Nothing here changes a registered verdict; ``gate4.json`` does that.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from phase0.corpus import read_tasks
from phase0.ground_truth import gold_files


def mcnemar_exact_p(b: int, c: int) -> float:
    """Two-sided exact binomial test on the discordant pairs (H0: b == c)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired_ci(n: int, b: int, c: int, z: float = 1.959964) -> tuple[float, float]:
    """Wald interval for the paired difference in proportions (treatment - control), in points."""
    if n == 0:
        return (0.0, 0.0)
    d = (c - b) / n
    var = ((b + c) / n - d * d) / n
    h = z * math.sqrt(max(var, 0.0))
    return (round(100 * (d - h), 2), round(100 * (d + h), 2))


def bootstrap_ci(ctl: list[int], trt: list[int], seed: int = 7, reps: int = 2000) -> tuple[float, float]:
    """Percentile bootstrap over tasks (resample pairs), lift in points."""
    n = len(ctl)
    if n == 0:
        return (0.0, 0.0)
    rng = random.Random(seed)
    diffs = []
    for _ in range(reps):
        s = 0
        for _ in range(n):
            i = rng.randrange(n)
            s += trt[i] - ctl[i]
        diffs.append(100 * s / n)
    diffs.sort()
    return (round(diffs[int(0.025 * reps)], 2), round(diffs[int(0.975 * reps) - 1], 2))


def summarise(rows: list[dict], label: str) -> dict:
    n = len(rows)
    b = sum(1 for r in rows if r["control_hit"] and not r["treatment_hit"])
    c = sum(1 for r in rows if r["treatment_hit"] and not r["control_hit"])
    both = sum(1 for r in rows if r["control_hit"] and r["treatment_hit"])
    ctl = [int(r["control_hit"]) for r in rows]
    trt = [int(r["treatment_hit"]) for r in rows]
    out = {
        "label": label, "n_tasks": n,
        "control_localized": sum(ctl), "treatment_localized": sum(trt),
        "control_rate": round(sum(ctl) / n, 4) if n else 0.0, "treatment_rate": round(sum(trt) / n, 4) if n else 0.0,
        "lift_pts": round(100 * (sum(trt) - sum(ctl)) / n, 2) if n else 0.0,
        "both_hit": both, "control_only_hit": b, "treatment_only_hit": c, "neither_hit": n - both - b - c,
        "mcnemar_exact_p": round(mcnemar_exact_p(b, c), 4),
        "lift_ci95_paired_wald_pts": paired_ci(n, b, c),
        "lift_ci95_bootstrap_pts": bootstrap_ci(ctl, trt),
        "flags_differed": sum(1 for r in rows if r["flags_differed"]),
        "flags_differed_rate": round(sum(1 for r in rows if r["flags_differed"]) / n, 4) if n else 0.0,
        "retrieved_any": sum(1 for r in rows if r["retrieved"]),
        "retrieval_coverage": round(sum(1 for r in rows if r["retrieved"]) / n, 4) if n else 0.0,
    }
    return out


def _rows_v2(a: dict, repo: str, arm: str) -> list[dict]:
    """Per-task rows from a v2 arms.json (hits recorded by the evaluator)."""
    c, t = a["arms"]["control"], a["arms"][arm]
    rows = []
    for iid, chit in c["hits"].items():
        if iid not in t["hits"]:
            continue
        rows.append({"instance_id": iid, "repo": repo, "control_hit": bool(chit), "treatment_hit": bool(t["hits"][iid]),
                     "flags_differed": c["flags"].get(iid) != t["flags"].get(iid), "retrieved": bool(t.get("retrieved", {}).get(iid))})
    return rows


def _rows_v1(a: dict, repo: str, tasks: dict) -> list[dict]:
    rows = []
    for iid, cflags in a["control_flags"].items():
        t = tasks.get(iid)
        if t is None:
            continue
        gold = set(gold_files(t.patch))
        if not gold:
            continue
        tflags = a["treatment_flags"].get(iid, [])
        rows.append({"instance_id": iid, "repo": repo, "control_hit": any(p in gold for p in cflags), "treatment_hit": any(p in gold for p in tflags),
                     "flags_differed": list(cflags) != list(tflags), "retrieved": bool(a.get("retrieved", {}).get(iid))})
    return rows


def analyse(tasks_path: Path | None, eval_dir: Path, negative_control: str | None, secondary_repos: list[str], arm: str = "treatment") -> dict:
    tasks = {t.instance_id: t for t in read_tasks(tasks_path)} if tasks_path else {}
    rows: list[dict] = []
    per_repo: dict[str, dict] = {}
    errors: dict[str, dict] = {}
    for f in sorted(eval_dir.glob("*.arms.json")):
        repo = f.name[: -len(".arms.json")].replace("__", "/", 1)
        a = json.loads(f.read_text())
        errors[repo] = a.get("errors", {})
        if "arms" in a and arm in a["arms"]:
            rrows = _rows_v2(a, repo, arm)
        elif tasks:
            rrows = _rows_v1(a, repo, tasks)
        else:
            raise SystemExit(f"{f}: no per-task hits in arms.json and no --tasks given to recompute them")
        per_repo[repo] = summarise(rrows, repo)
        if repo != negative_control:
            rows.extend(rrows)
    primary = summarise(rows, "primary: all treatment repos (registered)")
    secondary = summarise([r for r in rows if r["repo"] in set(secondary_repos)], "secondary: repos that passed Gate 3") if secondary_repos else None
    neg = per_repo.get(negative_control) if negative_control else None
    return {"arm": arm, "primary": primary, "secondary": secondary, "negative_control": neg, "per_repo": per_repo,
            "errors": {k: v for k, v in errors.items() if v}, "tasks": rows}


def render_md(rep: dict) -> str:
    def block(s: dict) -> str:
        return (f"**{s['label']}** — n = {s['n_tasks']}, control {s['control_rate']:.3f}, treatment {s['treatment_rate']:.3f}, "
                f"lift {s['lift_pts']:+.2f} pts (paired Wald 95% CI {s['lift_ci95_paired_wald_pts'][0]:+.1f} to {s['lift_ci95_paired_wald_pts'][1]:+.1f}; "
                f"bootstrap {s['lift_ci95_bootstrap_pts'][0]:+.1f} to {s['lift_ci95_bootstrap_pts'][1]:+.1f}). "
                f"Discordant pairs: treatment-only {s['treatment_only_hit']}, control-only {s['control_only_hit']}, McNemar exact p = {s['mcnemar_exact_p']}. "
                f"Flags differed on {s['flags_differed']}/{s['n_tasks']} tasks; memory retrieved on {s['retrieved_any']}/{s['n_tasks']}.\n")
    out = [f"# Paired analysis — arm `{rep.get('arm', 'treatment')}` vs control\n", block(rep["primary"])]
    if rep.get("secondary"):
        out.append(block(rep["secondary"]))
    if rep.get("negative_control"):
        out.append(block(rep["negative_control"]))
    out.append("\n| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
    for repo, s in rep["per_repo"].items():
        out.append(f"| {repo} | {s['n_tasks']} | {s['control_rate']:.3f} | {s['treatment_rate']:.3f} | {s['lift_pts']:+.2f} | {s['treatment_only_hit']} | {s['control_only_hit']} | {s['mcnemar_exact_p']} | {s['flags_differed']} | {s['retrieved_any']} |\n")
    if rep.get("errors"):
        out.append(f"\nTasks dropped from both arms after a failed call: {json.dumps({k: len(v) for k, v in rep['errors'].items()})}\n")
    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks"); ap.add_argument("--eval-dir", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--negative-control"); ap.add_argument("--secondary-repos", default="")
    ap.add_argument("--treatment-arm", default="treatment", help="v2: which memory arm to pair against control (treatment | ungated); every arm present is also written as paired-<arm>.*")
    args = ap.parse_args(argv)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    secondary = [r for r in args.secondary_repos.split(",") if r]
    rep = analyse(Path(args.tasks) if args.tasks else None, Path(args.eval_dir), args.negative_control, secondary, args.treatment_arm)
    (out / "paired.json").write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    (out / "paired.md").write_text(render_md(rep))
    print(render_md(rep))
    # every other memory arm present in the v2 files gets its own report
    names = set()
    for f in Path(args.eval_dir).glob("*.arms.json"):
        names |= set(json.loads(f.read_text()).get("arms", {}))
    for name in sorted(names - {"control", args.treatment_arm}):
        r2 = analyse(None, Path(args.eval_dir), args.negative_control, secondary, name)
        (out / f"paired-{name}.json").write_text(json.dumps(r2, indent=1, sort_keys=True) + "\n")
        (out / f"paired-{name}.md").write_text(render_md(r2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
