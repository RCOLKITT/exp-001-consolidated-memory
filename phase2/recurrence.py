"""Gold-location recurrence along each repo's chain — the corpus property
that decides whether file-level memory can be built at all (Gate 3's
"defects don't repeat" kill condition, measured before spending).

For each repo and build prefix N: how many gold files (and directories)
recur >= 3 times among the first N tasks, and what share of the remaining
(eval) tasks have a gold file / directory already seen >= 1 and >= 3 times.

    python -m phase2.recurrence corpus/tasks.jsonl --repos a/b,c/d --prefixes 20,40,60 --md out.md --json out.json
    # v2: function-level keys (path::qualname), needs the checkouts (or a functions.jsonl cache)
    python -m phase2.recurrence corpus/tasks.jsonl --repos a/b --level function --repos-dir corpus/repos --functions-cache runs/functions.jsonl
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

from phase0.chains import build_chains
from phase0.corpus import read_tasks
from phase0.functions import FunctionIndexCache, checkout_reader
from phase0.ground_truth import gold_files, gold_symbols


def dir_of(p: str) -> str:
    if "::" in p:                       # function key -> its file
        return p.split("::", 1)[0]
    return p.rsplit("/", 1)[0] if "/" in p else "."


def ceilings(res: dict, control_per_repo: dict) -> dict:
    """ceiling on lift (pts) per repo/prefix and aggregated, for promotion at >= 2 and >= 3 occurrences:
    seenK x (1 - p0), p0 = control hit@k of the repo."""
    out = {"per_repo": {}, "aggregate": {}}
    agg: dict = {}
    for repo, d in res.items():
        if repo.startswith("_"):
            continue
        p0 = control_per_repo.get(repo, {}).get("localization_rate")
        if p0 is None:
            continue
        for r in d["rows"]:
            if r["n_eval"] < 10 or r["prefix"] >= d["n_tasks"]:
                continue
            c2 = 100 * (r["eval_file_seen2"] or 0) * (1 - p0); c3 = 100 * (r["eval_file_seen3"] or 0) * (1 - p0)
            out["per_repo"].setdefault(repo, {})[str(r["prefix"])] = {"n_eval": r["n_eval"], "p0": p0, "ceiling_ge2": round(c2, 1), "ceiling_ge3": round(c3, 1)}
            a = agg.setdefault(str(r["prefix"]), {"eval": 0, "r2": 0.0, "r3": 0.0}); a["eval"] += r["n_eval"]; a["r2"] += r["n_eval"] * c2; a["r3"] += r["n_eval"] * c3
    for k, a in agg.items():
        out["aggregate"][k] = {"eval_pool": a["eval"], "ceiling_ge2": round(a["r2"] / a["eval"], 1), "ceiling_ge3": round(a["r3"] / a["eval"], 1)}
    return out


def analyse(tasks, repos, prefixes, gold_of=None):
    """`gold_of(task) -> keys` defaults to gold files; at function level pass
    `lambda t: gold_symbols(t, index)` (keys `path::qualname`; `dir_of` then
    groups by file, so the "dir" columns read as file-level recurrence)."""
    gold_of = gold_of or (lambda t: gold_files(t.patch))
    out = {}
    chains = {c.repo: c for c in build_chains(tasks)}
    for repo in repos:
        c = chains.get(repo)
        if c is None:
            continue
        golds = [set(gold_of(t)) for t in c.tasks]
        rows = []
        for n in prefixes + ["all"]:
            N = len(c.tasks) if n == "all" else min(int(n), len(c.tasks))
            fc, dc = collections.Counter(), collections.Counter()
            for g in golds[:N]:
                for f in g:
                    fc[f] += 1
                for d in {dir_of(f) for f in g}:
                    dc[d] += 1
            ev = golds[N:]
            seen1 = sum(1 for g in ev if any(fc.get(f, 0) >= 1 for f in g)); seen3 = sum(1 for g in ev if any(fc.get(f, 0) >= 3 for f in g))
            seen2 = sum(1 for g in ev if any(fc.get(f, 0) >= 2 for f in g))
            dseen1 = sum(1 for g in ev if any(dc.get(dir_of(f), 0) >= 1 for f in g)); dseen3 = sum(1 for g in ev if any(dc.get(dir_of(f), 0) >= 3 for f in g))
            rows.append({"prefix": N, "n_eval": len(ev), "files_ge3": sum(1 for v in fc.values() if v >= 3), "files_ge2": sum(1 for v in fc.values() if v >= 2),
                         "dirs_ge3": sum(1 for v in dc.values() if v >= 3), "distinct_files": len(fc), "distinct_dirs": len(dc),
                         "eval_file_seen1": round(seen1 / len(ev), 3) if ev else None, "eval_file_seen2": round(seen2 / len(ev), 3) if ev else None, "eval_file_seen3": round(seen3 / len(ev), 3) if ev else None,
                         "eval_dir_seen1": round(dseen1 / len(ev), 3) if ev else None, "eval_dir_seen3": round(dseen3 / len(ev), 3) if ev else None,
                         "top_files": fc.most_common(3)})
        out[repo] = {"n_tasks": len(c.tasks), "rows": rows}
    return out


def markdown(res):
    lines = ["# Gold-location recurrence along chains", "", "eval_file_seen3 = share of eval tasks whose gold file was a gold file >= 3 times in the build prefix (what file-level memory could at best recall).", "",
             "| repo | prefix | eval n | files >=3 | dirs >=3 | eval: file seen>=1 | file seen>=3 | dir seen>=1 | dir seen>=3 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for repo, d in res.items():
        if repo.startswith("_"):
            continue
        for r in d["rows"]:
            lines.append(f"| {repo} | {r['prefix']} | {r['n_eval']} | {r['files_ge3']} | {r['dirs_ge3']} | {r['eval_file_seen1']} | {r['eval_file_seen3']} | {r['eval_dir_seen1']} | {r['eval_dir_seen3']} |")
    return "\n".join(lines) + "\n"


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks"); ap.add_argument("--repos", required=True); ap.add_argument("--prefixes", default="20,40,60")
    ap.add_argument("--md"); ap.add_argument("--json", dest="json_out")
    ap.add_argument("--control-metrics", help="phase0 control metrics.json: adds ceilings on lift (seenK x (1 - p0))")
    ap.add_argument("--level", default="file", choices=["file", "function"]); ap.add_argument("--repos-dir", default="corpus/repos"); ap.add_argument("--functions-cache")
    a = ap.parse_args(argv)
    gold_of = None
    if a.level == "function":
        index = FunctionIndexCache(checkout_reader(a.repos_dir), a.functions_cache)
        gold_of = lambda t: gold_symbols(t, index)
    res = analyse(read_tasks(a.tasks), [r.strip() for r in a.repos.split(",") if r.strip()], [int(x) for x in a.prefixes.split(",")], gold_of)
    res["_level"] = a.level
    md = markdown(res).replace("# Gold-location recurrence along chains", f"# Gold-location recurrence along chains (level: {a.level})")
    if a.control_metrics:
        c = ceilings(res, json.loads(Path(a.control_metrics).read_text())["per_repo"])
        res["_ceilings"] = c
        md += "\n## Ceiling on lift (pts) = seenK x (1 - p0)\n\n| build N | eval pool | promote at >= 2 | promote at >= 3 |\n|---:|---:|---:|---:|\n"
        md += "\n".join(f"| {k} | {v['eval_pool']} | {v['ceiling_ge2']} | {v['ceiling_ge3']} |" for k, v in sorted(c["aggregate"].items(), key=lambda kv: int(kv[0]))) + "\n"
    if a.md: Path(a.md).parent.mkdir(parents=True, exist_ok=True); Path(a.md).write_text(md)
    if a.json_out: Path(a.json_out).write_text(json.dumps(res, indent=1))
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
