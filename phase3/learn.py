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
from adapters.code.policy import CODE_PROMOTION_POLICY, RHO_REINFORCE, THETA_SURPRISE
from memkernel import KernelConfig
from memkernel.kernel import counting_clock
from memkernel.persist import save_kernel
from adapters.code.similarity import FileKeyedSimilarity, make_similarity
from phase0.chains import build_chains
from phase0.corpus import apply_freshness, read_tasks
from phase0.ground_truth import ground_truth_from_tasks
from phase0.run_control import ensure_checkout, repo_dir
from phase0.verifier import CachedClient, Localizer, make_client, repo_file_tree


def similarity(args, cache_path=None):
    """The similarity seam, chosen on the command line. `embedding` is the
    pre-registered seam (pinned model + revision, vectors cached with the run)."""
    return make_similarity(args.similarity, cache_path, args.embedding_model, args.embedding_revision)


def kernel_config(ttl_ticks: int, theta: float = THETA_SURPRISE, cluster: float = CODE_PROMOTION_POLICY.cluster_similarity, rho: float = RHO_REINFORCE,
                  min_occurrences: int = CODE_PROMOTION_POLICY.min_occurrences, min_distinct_inputs: int = CODE_PROMOTION_POLICY.min_distinct_inputs) -> KernelConfig:
    from dataclasses import replace
    return KernelConfig(theta_surprise=theta, reinforce_min_sim=rho, ttl_ticks=ttl_ticks,
                        policy=replace(CODE_PROMOTION_POLICY, cluster_similarity=cluster, min_occurrences=min_occurrences, min_distinct_inputs=min_distinct_inputs))


def add_seam_args(ap):
    ap.add_argument("--similarity", default="embedding", choices=["jaccard", "hashing", "embedding"])
    ap.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--embedding-revision", default=None, help="Hub commit sha — pre-registration value")
    ap.add_argument("--theta", type=float, default=THETA_SURPRISE, help="Θ_surprise (pre-registration value, from phase2.tune)")
    ap.add_argument("--cluster-similarity", type=float, default=CODE_PROMOTION_POLICY.cluster_similarity)
    ap.add_argument("--rho", type=float, default=RHO_REINFORCE, help="reinforce_min_sim (pre-registration value, D22/D23)")
    ap.add_argument("--consolidation", default="file", choices=["file", "embedding"], help="what makes two records the same pattern (D24): same file, or embedding similarity")
    ap.add_argument("--min-occurrences", type=int, default=CODE_PROMOTION_POLICY.min_occurrences, help="promotion: bad records needed (pre-registration value, D25)")
    ap.add_argument("--min-distinct-inputs", type=int, default=CODE_PROMOTION_POLICY.min_distinct_inputs, help="promotion: distinct tasks needed (D25)")


def make_pipeline(repo, tasks, args, cache_path):
    truth = ground_truth_from_tasks(tasks)
    client = CachedClient(None if args.offline else make_client(args.provider, args.base_url, args.api_key_env, args.model_extra), cache_path, offline=args.offline)
    loc = Localizer(client, args.model, k=args.top_k, effort=args.effort)
    repos_dir = Path(args.repos_dir)
    list_files = lambda t: repo_file_tree(ensure_checkout(repos_dir, t))
    sem = similarity(args, Path(cache_path).with_name("embeddings.jsonl"))       # semantic: retrieval (and consolidation if chosen)
    cons = FileKeyedSimilarity(sem) if args.consolidation == "file" else sem     # D24
    return RepoPipeline(repo, loc, cons, truth, kernel_config(args.ttl, args.theta, args.cluster_similarity, args.rho, args.min_occurrences, args.min_distinct_inputs), list_files, counting_clock(),
                        retrieval_similarity=sem)


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", required=True); ap.add_argument("--split", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--models"); ap.add_argument("--repos-dir", default="corpus/repos")
    ap.add_argument("--model", default="claude-opus-5"); ap.add_argument("--effort", default="high"); ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--provider", default="anthropic", choices=["anthropic", "openai-compatible"]); ap.add_argument("--base-url"); ap.add_argument("--api-key-env", default="MODEL_API_KEY"); ap.add_argument("--model-extra", default="")
    add_seam_args(ap)
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
        stats["similarity"] = getattr(p.kernel.similarity, "name", args.similarity); stats["theta"] = args.theta; stats["cluster_similarity"] = args.cluster_similarity; stats["rho"] = args.rho; stats["min_occurrences"] = args.min_occurrences; stats["min_distinct_inputs"] = args.min_distinct_inputs; stats["consolidation"] = getattr(p.kernel.similarity, "name", args.consolidation); stats["retrieval"] = getattr(p.kernel.retrieval_similarity, "name", "")
        write_json(stats, rd / "gate3.json")
        sys.stderr.write(f"{chain.repo}: {len(build)} build tasks, discard_rate={stats['discard_rate']}, promoted={stats['promoted']}, version={version[:12]}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
