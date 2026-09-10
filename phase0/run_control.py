"""Phase 0 control-arm run: freshness gate -> checkout -> localize -> score.

    python -m phase0.run_control --tasks corpus/tasks.jsonl --models corpus/models.json \
        --repos-dir corpus/repos --out runs/control-001 --model claude-opus-5 --top-k 3 [--limit N]

    # determinism check (Gate 0 item 3): rerun offline from the same cache and diff
    python -m phase0.run_control ... --out runs/control-002 --cache runs/control-001/cache.jsonl --offline
    python -m phase0.run_control --compare runs/control-001 runs/control-002

Repos are cloned once into --repos-dir/<owner>__<name> and checked out at
each task's base_commit (detached). No dependency install, no Docker:
file-level localization only needs the tree (docs/DECISIONS.md D8).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from .corpus import Task, apply_freshness, read_tasks
from .ground_truth import ground_truth_from_tasks
from .metrics import dump, score
from .verifier import CachedClient, Localizer, make_client, repo_file_tree


def repo_dir(repos_dir: Path, repo: str) -> Path:
    return repos_dir / repo.replace("/", "__")


def ensure_checkout(repos_dir: Path, task: Task) -> Path:
    d = repo_dir(repos_dir, task.repo)
    if not (d / ".git").exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", f"https://github.com/{task.repo}.git", str(d)], check=True)
    head = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    if not head.startswith(task.base_commit):
        r = subprocess.run(["git", "-C", str(d), "checkout", "--quiet", "--force", task.base_commit], capture_output=True, text=True)
        if r.returncode != 0:
            subprocess.run(["git", "-C", str(d), "fetch", "--quiet", "origin", task.base_commit], check=True)
            subprocess.run(["git", "-C", str(d), "checkout", "--quiet", "--force", task.base_commit], check=True)
    return d


def run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tasks = read_tasks(args.tasks)
    if args.models:
        tasks = apply_freshness(tasks, args.models, out / "freshness.jsonl")
    tasks.sort(key=lambda t: (t.repo, t.created_at, t.instance_id))
    if args.limit:
        tasks = tasks[: args.limit]
    truth = ground_truth_from_tasks(tasks)
    repo_of = {t.instance_id: t.repo for t in tasks}

    cache_path = Path(args.cache) if args.cache else out / "cache.jsonl"
    inner = None if args.offline else make_client(args.provider, args.base_url, args.api_key_env)
    client = CachedClient(inner, cache_path, offline=args.offline)
    localizer = Localizer(client, args.model, k=args.top_k, effort=args.effort)

    flags_path = out / "flags.jsonl"
    flags_by_task = {}
    t0 = time.time()
    with flags_path.open("w") as f:
        for i, t in enumerate(tasks, 1):
            d = ensure_checkout(Path(args.repos_dir), t)
            files = repo_file_tree(d)
            res = localizer.localize(t.instance_id, t.problem_statement, files)
            flags_by_task[t.instance_id] = res.flags()
            f.write(json.dumps({"instance_id": t.instance_id, "repo": t.repo, "ranked": list(res.ranked), "request_key": res.request_key}, sort_keys=True) + "\n")
            sys.stderr.write(f"[{i}/{len(tasks)}] {t.instance_id}: {[p for p, _ in res.ranked]}\n")
    m = score(flags_by_task, truth, repo_of)
    dump(m, out / "metrics.json")
    manifest = {
        "model": args.model, "provider": args.provider, "base_url": args.base_url, "effort": args.effort, "top_k": args.top_k, "n_tasks": len(tasks),
        "offline": args.offline, "cache": str(cache_path), "cache_hits": client.hits, "cache_misses": client.misses,
        "flags_sha256": hashlib.sha256(flags_path.read_bytes()).hexdigest(),
        "elapsed_s": round(time.time() - t0, 1),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    sys.stdout.write(json.dumps({"localization_rate": m.localization_rate, "false_positive_rate": m.false_positive_rate, **manifest}, indent=1) + "\n")
    return 0


def compare(a: str, b: str) -> int:
    ma, mb = json.loads(Path(a, "manifest.json").read_text()), json.loads(Path(b, "manifest.json").read_text())
    same = ma["flags_sha256"] == mb["flags_sha256"]
    sys.stdout.write(f"flags identical: {same}\n  {a}: {ma['flags_sha256']}\n  {b}: {mb['flags_sha256']}\n")
    return 0 if same else 1


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"))
    ap.add_argument("--tasks")
    ap.add_argument("--models")
    ap.add_argument("--repos-dir", default="corpus/repos")
    ap.add_argument("--out")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--provider", default="anthropic", choices=["anthropic", "openai-compatible"])
    ap.add_argument("--base-url", help="openai-compatible: e.g. https://api.together.xyz/v1")
    ap.add_argument("--api-key-env", default="MODEL_API_KEY", help="openai-compatible: env var holding the key")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cache", help="reuse an existing cache file (default: <out>/cache.jsonl)")
    ap.add_argument("--offline", action="store_true", help="never call the model; fail on cache miss")
    args = ap.parse_args(argv)
    if args.compare:
        return compare(*args.compare)
    if not (args.tasks and args.out):
        ap.error("--tasks and --out are required")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
