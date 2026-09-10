"""Phase 3 — learning phase: build-split chains through the treatment pipeline.

    python -m phase3.learn --tasks corpus/tasks.jsonl --split corpus/split.json \
        --repos-dir corpus/repos --out runs/learn-001 --model claude-opus-5 [--negative-control owner/name]

`corpus/split.json` = {"owner/name": N} — N build tasks per repo, chronological
(pre-registration value). The negative-control repo is skipped: it receives
no memory-building runs (spec Phase 2 item 3). Output per repo:
`runs/learn-001/<owner>__<name>/kernel.json` + `gate3.json`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adapters.code.pipeline import RepoPipeline, write_json
from adapters.code.policy import CODE_PROMOTION_POLICY, THETA_SURPRISE
from memkernel import KernelConfig
from memkernel.kernel import counting_clock
from memkernel.persist import save_kernel
from memkernel.seams import TokenJaccardSimilarity
from phase0.chains import build_chains
from phase0.corpus import apply_freshness, read_tasks
from phase0.ground_truth import ground_truth_from_tasks
from phase0.run_control import ensure_checkout, repo_dir
from phase0.verifier import CachedClient, Localizer, make_client, repo_file_tree


def similarity():
    # TODO(Phase 2): replace with EmbeddingCosineSimilarity over a pinned, cached embedding model.
    return TokenJaccardSimilarity()


def kernel_config(ttl_ticks: int) -> KernelConfig:
    return KernelConfig(theta_surprise=THETA_SURPRISE, ttl_ticks=ttl_ticks, policy=CODE_PROMOTION_POLICY)


def make_pipeline(repo, tasks, args, cache_path):
    truth = ground_truth_from_tasks(tasks)
    client = CachedClient(None if args.offline else make_client(args.provider, args.base_url, args.api_key_env), cache_path, offline=args.offline)
    loc = Localizer(client, args.model, k=args.top_k, effort=args.effort)
    repos_dir = Path(args.repos_dir)
    list_files = lambda t: repo_file_tree(ensure_checkout(repos_dir, t))
    return RepoPipeline(repo, loc, similarity(), truth, kernel_config(args.ttl), list_files, counting_clock())


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", required=True); ap.add_argument("--split", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--models"); ap.add_argument("--repos-dir", default="corpus/repos")
    ap.add_argument("--model", default="claude-opus-5"); ap.add_argument("--effort", default="high"); ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--provider", default="anthropic", choices=["anthropic", "openai-compatible"]); ap.add_argument("--base-url"); ap.add_argument("--api-key-env", default="MODEL_API_KEY")
    ap.add_argument("--ttl", type=int, default=30, help="buffer TTL in tasks (one tick per task)")
    ap.add_argument("--negative-control"); ap.add_argument("--cache"); ap.add_argument("--offline", action="store_true")
    args = ap.parse_args(argv)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    tasks = read_tasks(args.tasks)
    if args.models:
        tasks = apply_freshness(tasks, args.models, out / "freshness.jsonl")
    split = json.loads(Path(args.split).read_text())
    for chain in build_chains(tasks):
        if chain.repo not in split or chain.repo == args.negative_control:
            continue
        build, _ = chain.split(int(split[chain.repo]))
        rd = out / chain.repo.replace("/", "__")
        p = make_pipeline(chain.repo, chain.tasks, args, Path(args.cache) if args.cache else rd / "cache.jsonl")
        version = p.learn(build)
        save_kernel(p.kernel, rd / "kernel.json")
        stats = p.gate3_stats(); stats["n_build"] = len(build)
        write_json(stats, rd / "gate3.json")
        sys.stderr.write(f"{chain.repo}: {len(build)} build tasks, discard_rate={stats['discard_rate']}, promoted={stats['promoted']}, version={version[:12]}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
