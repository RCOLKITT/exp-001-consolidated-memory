"""Gold-location recurrence along each repo's chain — the corpus property
that decides whether file-level memory can be built at all (Gate 3's
"defects don't repeat" kill condition, measured before spending).

For each repo and build prefix N: how many gold files (and directories)
recur >= 3 times among the first N tasks, and what share of the remaining
(eval) tasks have a gold file / directory already seen >= 1 and >= 3 times.

    python -m phase2.recurrence corpus/tasks.jsonl --repos a/b,c/d --prefixes 20,40,60 --md out.md --json out.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

from phase0.chains import build_chains
from phase0.corpus import read_tasks
from phase0.ground_truth import gold_files


def dir_of(p: str) -> str:
    return p.rsplit("/", 1)[0] if "/" in p else "."


def analyse(tasks, repos, prefixes):
    out = {}
    chains = {c.repo: c for c in build_chains(tasks)}
    for repo in repos:
        c = chains.get(repo)
        if c is None:
            continue
        golds = [set(gold_files(t.patch)) for t in c.tasks]
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
            dseen1 = sum(1 for g in ev if any(dc.get(dir_of(f), 0) >= 1 for f in g)); dseen3 = sum(1 for g in ev if any(dc.get(dir_of(f), 0) >= 3 for f in g))
            rows.append({"prefix": N, "n_eval": len(ev), "files_ge3": sum(1 for v in fc.values() if v >= 3), "files_ge2": sum(1 for v in fc.values() if v >= 2),
                         "dirs_ge3": sum(1 for v in dc.values() if v >= 3), "distinct_files": len(fc), "distinct_dirs": len(dc),
                         "eval_file_seen1": round(seen1 / len(ev), 3) if ev else None, "eval_file_seen3": round(seen3 / len(ev), 3) if ev else None,
                         "eval_dir_seen1": round(dseen1 / len(ev), 3) if ev else None, "eval_dir_seen3": round(dseen3 / len(ev), 3) if ev else None,
                         "top_files": fc.most_common(3)})
        out[repo] = {"n_tasks": len(c.tasks), "rows": rows}
    return out


def markdown(res):
    lines = ["# Gold-location recurrence along chains", "", "eval_file_seen3 = share of eval tasks whose gold file was a gold file >= 3 times in the build prefix (what file-level memory could at best recall).", "",
             "| repo | prefix | eval n | files >=3 | dirs >=3 | eval: file seen>=1 | file seen>=3 | dir seen>=1 | dir seen>=3 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for repo, d in res.items():
        for r in d["rows"]:
            lines.append(f"| {repo} | {r['prefix']} | {r['n_eval']} | {r['files_ge3']} | {r['dirs_ge3']} | {r['eval_file_seen1']} | {r['eval_file_seen3']} | {r['eval_dir_seen1']} | {r['eval_dir_seen3']} |")
    return "\n".join(lines) + "\n"


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks"); ap.add_argument("--repos", required=True); ap.add_argument("--prefixes", default="20,40,60")
    ap.add_argument("--md"); ap.add_argument("--json", dest="json_out")
    a = ap.parse_args(argv)
    res = analyse(read_tasks(a.tasks), [r.strip() for r in a.repos.split(",") if r.strip()], [int(x) for x in a.prefixes.split(",")])
    md = markdown(res)
    if a.md: Path(a.md).parent.mkdir(parents=True, exist_ok=True); Path(a.md).write_text(md)
    if a.json_out: Path(a.json_out).write_text(json.dumps(res, indent=1))
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
