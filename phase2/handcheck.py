"""Oracle hand-check (Gate 2 item 3): oracle vs manual labels on 50 flags.

    python -m phase2.handcheck export runs/control-001/flags.jsonl corpus/tasks.jsonl --n 50 --seed 1 --out handcheck.csv
    # fill the `manual` column with good|bad|unknown by reading the patch, then
    python -m phase2.handcheck score handcheck.csv     # prints agreement, exit 1 if < 0.95

The reviewer sees the flagged file and the gold patch, never the verifier's
reasoning, so the check tests the oracle, not the verifier.

v2 (Gate 2.3-v2, function-level ground truth):
    python -m phase2.handcheck export-functions corpus/tasks.jsonl --repos a/b,c/d --repos-dir corpus/repos --n 50 --seed 1 --out handcheck-functions.csv
    # the reviewer reads `context` (the pre-image lines around the hunk) and fills `manual` with the enclosing def/class qualname or <module>
    python -m phase2.handcheck verify-functions handcheck-functions.csv --out verified.csv   # indentation-based parser, independent of `ast`
    python -m phase2.handcheck score handcheck-functions.csv                                   # manual vs oracle agreement
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

from phase0.corpus import read_tasks
from phase0.ground_truth import ground_truth_from_tasks
from phase0.verifier import file_location

from adapters.code.oracle import Flag

THRESHOLD = 0.95


def sample_flags(flags_rows: list[dict], n: int, seed: int) -> list[tuple[str, str]]:
    pairs = [(r["instance_id"], item[0]) for r in flags_rows for item in r["ranked"]]   # item = (path, reason) or (path, qualname, reason)
    rng = random.Random(seed)
    rng.shuffle(pairs)
    return sorted(pairs[:n])


def export(flags_path: str, tasks_path: str, n: int, seed: int, out: str) -> int:
    rows = [json.loads(l) for l in Path(flags_path).read_text().splitlines() if l.strip()]
    tasks = {t.instance_id: t for t in read_tasks(tasks_path)}
    truth = ground_truth_from_tasks(tasks.values())
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance_id", "flagged_path", "oracle", "manual", "gold_files"])
        for iid, path in sample_flags(rows, n, seed):
            gt = truth.locations(iid) or ()
            oracle = "unknown" if truth.locations(iid) is None else ("bad" if any(file_location(path).overlaps(h) for h in gt) else "good")
            w.writerow([iid, path, oracle, "", ";".join(sorted({h.path for h in gt}))])
    return 0


def independent_gold_files(patch: str) -> set[str]:
    """Second, deliberately different parser: files named on `+++ b/` lines
    (and `--- a/` for deletions), no hunk parsing, test paths dropped by a
    separate rule. Disagreement with phase0.ground_truth flags an oracle bug."""
    files: set[str] = set()
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            files.add(line[6:].strip())
        elif line.startswith("--- a/") and not line.endswith("/dev/null"):
            files.add(line[6:].strip())
    def is_test(p: str) -> bool:
        parts = p.lower().split("/")
        return any(x in ("test", "tests", "testing") for x in parts[:-1]) or parts[-1].startswith("test_") or parts[-1].endswith("_test.py") or parts[-1] == "conftest.py"
    return {f for f in files if not is_test(f)}


def verify(csv_path: str, tasks_path: str, out_path: str) -> tuple[float, int, int]:
    """Fill `manual` from the independent parser and score agreement with the oracle."""
    tasks = {t.instance_id: t for t in read_tasks(tasks_path)}
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        t = tasks.get(r["instance_id"])
        gold = independent_gold_files(t.patch) if t else set()
        r["manual"] = "unknown" if t is None else ("bad" if r["flagged_path"] in gold else "good")
        r["independent_gold_files"] = ";".join(sorted(gold))
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return agreement(out_path)


def agreement(csv_path: str) -> tuple[float, int, int]:
    with open(csv_path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["manual"].strip()]
    if not rows:
        return 0.0, 0, 0
    agree = sum(1 for r in rows if r["manual"].strip() == r["oracle"])
    return agree / len(rows), agree, len(rows)


# --------------------------------------------------------------------------
# v2: hunk -> enclosing symbol
# --------------------------------------------------------------------------
import re

_DEF_RE = re.compile(r"^(\s*)(?:async\s+)?(def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")


def indent_symbols(source: str) -> list[tuple[str, int, int]]:
    """Independent symboliser: `def`/`class` lines and their blocks found by
    indentation only (no `ast`). Returns (qualname, start, end) for top-level
    defs, classes and their direct methods; decorators extend the start."""
    lines = source.splitlines()
    heads = []
    for i, line in enumerate(lines, 1):
        m = _DEF_RE.match(line)
        if m:
            heads.append((i, len(m.group(1).expandtabs(8)), m.group(2), m.group(3)))
    out: list[tuple[str, int, int]] = []
    for j, (ln, ind, kind, name) in enumerate(heads):
        end = len(lines)
        for k in range(ln, len(lines)):
            text = lines[k]
            if text.strip() and not text.lstrip().startswith("#") and len(text) - len(text.lstrip()) <= ind and k + 1 > ln:
                end = k
                break
        while end > ln and not lines[end - 1].strip():
            end -= 1
        start = ln
        while start > 1 and lines[start - 2].lstrip().startswith("@") and len(lines[start - 2]) - len(lines[start - 2].lstrip()) == ind:
            start -= 1
        if ind == 0:
            out.append((name, start, end))
        else:
            parent = next((h for h in reversed(heads[:j]) if h[1] < ind and h[2] == "class"), None)
            if parent and parent[1] == 0 and not any(h[1] < ind and h[1] > parent[1] for h in heads[:j] if h[0] > parent[0]):
                out.append((f"{parent[3]}.{name}", start, end))
    return out


def export_functions(tasks_path: str, repos: list[str], repos_dir: str, n: int, seed: int, out: str, functions_cache: str | None = None) -> int:
    from phase0.functions import MODULE, FunctionIndexCache, checkout_reader, enclosing_range
    from phase0.ground_truth import is_test_path, parse_patch
    tasks = [t for t in read_tasks(tasks_path) if not repos or t.repo in repos]
    hunks = [(t, h) for t in tasks for h in parse_patch(t.patch).hunks if not is_test_path(h.path)]
    rng = random.Random(seed); rng.shuffle(hunks)
    reader = checkout_reader(repos_dir)
    index = FunctionIndexCache(reader, functions_cache)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance_id", "path", "hunk_start", "hunk_end", "oracle", "manual", "context"])
        for t, h in sorted(hunks[:n], key=lambda th: (th[0].instance_id, th[1].path, th[1].start_line)):
            spans = index.spans(t.repo, t.base_commit, h.path)
            oracle = ";".join(enclosing_range(spans, h.start_line, h.end_line)) if spans else MODULE
            src = reader(t.repo, t.base_commit, h.path)
            lines = src.splitlines() if src else []
            lo, hi = max(h.start_line - 3, 1), min(max(h.end_line, h.start_line) + 3, len(lines))
            context = "\n".join(f"{i}: {lines[i - 1]}" for i in range(lo, hi + 1)) if lines else "(file absent at base_commit)"
            w.writerow([t.instance_id, h.path, h.start_line, h.end_line, oracle, "", context])
    return 0


def verify_functions_with_tasks(csv_path: str, tasks_path: str, repos_dir: str, out_path: str) -> tuple[float, int, int]:
    tasks = {t.instance_id: t for t in read_tasks(tasks_path)}
    from phase0.functions import checkout_reader
    return verify_functions(csv_path, out_path, lambda iid, path: _read_at(checkout_reader(repos_dir), tasks, iid, path))


def _read_at(reader, tasks, iid, path):
    t = tasks.get(iid)
    return reader(t.repo, t.base_commit, path) if t else None


def verify_functions(csv_path: str, out_path: str, read_source) -> tuple[float, int, int]:
    """`read_source(instance_id, path) -> str | None`; fills `manual` from `indent_symbols` and scores agreement with `oracle`."""
    from phase0.functions import MODULE
    rows = list(csv.DictReader(open(csv_path, newline="")))
    agree = 0
    cache: dict[tuple, list] = {}
    for r in rows:
        key = (r["instance_id"], r["path"])
        if key not in cache:
            src = read_source(r["instance_id"], r["path"])
            cache[key] = indent_symbols(src) if src else []
        syms = cache[key]
        names = []
        for line in range(max(int(r["hunk_start"]), 1), max(int(r["hunk_end"]), int(r["hunk_start"]), 1) + 1):
            inner = [s for s in syms if s[1] <= line <= s[2]]
            name = min(inner, key=lambda s: s[2] - s[1])[0] if inner else MODULE
            if name not in names:
                names.append(name)
        r["manual"] = ";".join(names or [MODULE])
        agree += r["manual"] == r["oracle"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["instance_id"]); w.writeheader(); w.writerows(rows)
    return (agree / len(rows) if rows else 0.0), agree, len(rows)


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export"); e.add_argument("flags"); e.add_argument("tasks"); e.add_argument("--n", type=int, default=50); e.add_argument("--seed", type=int, default=1); e.add_argument("--out", required=True)
    s = sub.add_parser("score"); s.add_argument("csv")
    v = sub.add_parser("verify", help="fill `manual` with an independent patch parser and score"); v.add_argument("csv"); v.add_argument("tasks"); v.add_argument("--out", required=True)
    ef = sub.add_parser("export-functions", help="v2: sample gold hunks with their oracle symbol and source context for a human read")
    ef.add_argument("tasks"); ef.add_argument("--repos", default=""); ef.add_argument("--repos-dir", default="corpus/repos"); ef.add_argument("--functions-cache"); ef.add_argument("--n", type=int, default=50); ef.add_argument("--seed", type=int, default=1); ef.add_argument("--out", required=True)
    vf = sub.add_parser("verify-functions", help="v2: fill `manual` with an indentation-based symboliser (independent of ast) and score"); vf.add_argument("csv"); vf.add_argument("tasks"); vf.add_argument("--repos-dir", default="corpus/repos"); vf.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "export-functions":
        return export_functions(a.tasks, [r for r in a.repos.split(",") if r], a.repos_dir, a.n, a.seed, a.out, a.functions_cache)
    if a.cmd == "verify-functions":
        rate, agree, n = verify_functions_with_tasks(a.csv, a.tasks, a.repos_dir, a.out)
        print(f"independent-symboliser agreement {agree}/{n} = {rate:.3f} (threshold {THRESHOLD})")
        return 0 if n and rate >= THRESHOLD else 1
    if a.cmd == "export":
        return export(a.flags, a.tasks, a.n, a.seed, a.out)
    if a.cmd == "verify":
        rate, agree, n = verify(a.csv, a.tasks, a.out)
        print(f"independent-parser agreement {agree}/{n} = {rate:.3f} (threshold {THRESHOLD})")
        return 0 if n and rate >= THRESHOLD else 1
    rate, agree, n = agreement(a.csv)
    print(f"agreement {agree}/{n} = {rate:.3f} (threshold {THRESHOLD})")
    return 0 if n and rate >= THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
