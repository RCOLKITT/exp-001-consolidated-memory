"""Prequential (rolling) recurrence: every task after a warm-up is an eval
task scored against everything before it in its repo's chain.

    python -m phase2.prequential corpus/tasks.jsonl --min-chain 21 --warmup 20 --repos-dir checkouts \
        --functions-cache runs/functions.jsonl --md out.md --json out.json [--exclude a/b,c/d]

For each repo with chain >= warmup + 1 and each task t >= warmup: was any of
its gold keys already a gold key >= 1 / 2 / 3 times among tasks < t? Reported
at three granularities from the same Python-source-only hunks (D32 rule):
  file      path
  class     path::top-level symbol   (Class for Class.method; func; <module>)
  function  path::qualname
The pool is chain - warmup per repo, and the window behind each eval task is
the whole chain before it, which is what a deployed memory sees.
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
from phase0.ground_truth import gold_symbols

LEVELS = ("file", "class", "function")


def keys_at(level: str, symbols: tuple[str, ...]) -> set[str]:
    if level == "function":
        return set(symbols)
    if level == "class":
        return {f"{k.split('::', 1)[0]}::{k.split('::', 1)[1].split('.', 1)[0]}" for k in symbols}
    return {k.split("::", 1)[0] for k in symbols}


def analyse(tasks, warmup: int, min_chain: int, gold_symbols_of, exclude: set[str]) -> dict:
    out: dict = {"warmup": warmup, "min_chain": min_chain, "repos": {}, "aggregate": {}}
    totals = {lv: collections.Counter() for lv in LEVELS}
    for chain in build_chains(tasks):
        if chain.repo in exclude or len(chain.tasks) < min_chain:
            continue
        syms = [gold_symbols_of(t) for t in chain.tasks]
        per = {lv: {"n_eval": 0, "seen1": 0, "seen2": 0, "seen3": 0, "no_gold": 0} for lv in LEVELS}
        counters = {lv: collections.Counter() for lv in LEVELS}
        for i, s in enumerate(syms):
            for lv in LEVELS:
                keys = keys_at(lv, s)
                if i >= warmup:
                    p = per[lv]
                    p["n_eval"] += 1
                    if not keys:
                        p["no_gold"] += 1
                    else:
                        fc = counters[lv]
                        for k, name in ((1, "seen1"), (2, "seen2"), (3, "seen3")):
                            if any(fc.get(x, 0) >= k for x in keys):
                                p[name] += 1
                for x in keys:
                    counters[lv][x] += 1
        rec = {"chain": len(chain.tasks)}
        for lv in LEVELS:
            p = per[lv]; n = p["n_eval"]
            rec[lv] = {"n_eval": n, "n_scorable": n - p["no_gold"], **{k: round(p[k] / n, 3) if n else None for k in ("seen1", "seen2", "seen3")}}
            totals[lv].update({"n_eval": n, "n_scorable": n - p["no_gold"], "seen1": p["seen1"], "seen2": p["seen2"], "seen3": p["seen3"]})
        out["repos"][chain.repo] = rec
    for lv in LEVELS:
        t = totals[lv]; n = t["n_eval"]
        out["aggregate"][lv] = {"n_repos": len(out["repos"]), "n_eval": n, "n_scorable": t["n_scorable"], **{k: round(t[k] / n, 3) if n else None for k in ("seen1", "seen2", "seen3")}}
    return out


def markdown(res: dict) -> str:
    lines = [f"# Prequential recurrence (warm-up {res['warmup']}, chains >= {res['min_chain']}, Python-source gold only)", "",
             "seenK = share of eval tasks with a gold key already gold >= K times earlier in the chain.", "",
             "| repo | chain | eval | file seen2 | class seen2 | function seen2 | function seen1 | function seen3 | scorable |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for repo, r in sorted(res["repos"].items(), key=lambda kv: -kv[1]["chain"]):
        lines.append(f"| {repo} | {r['chain']} | {r['function']['n_eval']} | {r['file']['seen2']} | {r['class']['seen2']} | {r['function']['seen2']} | {r['function']['seen1']} | {r['function']['seen3']} | {r['function']['n_scorable']} |")
    a = res["aggregate"]
    lines += ["", "| level | repos | eval pool | scorable | seen1 | seen2 | seen3 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for lv in LEVELS:
        lines.append(f"| {lv} | {a[lv]['n_repos']} | {a[lv]['n_eval']} | {a[lv]['n_scorable']} | {a[lv]['seen1']} | {a[lv]['seen2']} | {a[lv]['seen3']} |")
    return "\n".join(lines) + "\n"


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks"); ap.add_argument("--warmup", type=int, default=20); ap.add_argument("--min-chain", type=int, default=21)
    ap.add_argument("--exclude", default=""); ap.add_argument("--repos-dir", default="corpus/repos"); ap.add_argument("--functions-cache")
    ap.add_argument("--md"); ap.add_argument("--json", dest="json_out")
    a = ap.parse_args(argv)
    index = FunctionIndexCache(checkout_reader(a.repos_dir), a.functions_cache)
    res = analyse(read_tasks(a.tasks), a.warmup, a.min_chain, lambda t: gold_symbols(t, index), {x for x in a.exclude.split(",") if x})
    md = markdown(res)
    if a.md: Path(a.md).parent.mkdir(parents=True, exist_ok=True); Path(a.md).write_text(md)
    if a.json_out: Path(a.json_out).write_text(json.dumps(res, indent=1))
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
