"""Threshold tuning on synthetic streams for a given similarity seam (D14).

Sweeps Θ_surprise × cluster_similarity and reports, per cell:
  discard_rate   fraction of candidate writes not buffered as new entries
                 (target: the injected redundant fraction)
  promoted       memories promoted by the end of the stream
  purity         fraction of promoted memories whose provenance is one pattern
  merged         fraction of promoted memories mixing >1 pattern (bad)

    python -m phase2.tune --similarity hashing --out results/phase2/tune-hashing.md
    python -m phase2.tune --similarity embedding --embedding-revision <sha> --out …
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adapters.code.similarity import make_similarity
from memkernel import Kernel, KernelConfig, PromotionPolicy
from memkernel.kernel import counting_clock
from memkernel.seams import PassthroughOracle
from memkernel.synthetic import StreamSpec, expected_redundant, generate, pattern_of


class MemoSimilarity:
    """Pairwise memo around any seam. The stream is identical across sweep
    cells, so every (a, b) pair is computed once for the whole sweep."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.name = getattr(inner, "name", type(inner).__name__)
        self._memo: dict[tuple[str, str], float] = {}

    def sim(self, a: str, b: str) -> float:
        k = (a, b) if a <= b else (b, a)
        v = self._memo.get(k)
        if v is None:
            v = self.inner.sim(a, b)
            self._memo[k] = v
        return v


def run_cell(similarity, theta: float, cluster: float, spec: StreamSpec, ttl: int = 10_000, schedule: int = 10, records=None) -> dict:
    records = records if records is not None else generate(spec)
    cfg = KernelConfig(theta_surprise=theta, ttl_ticks=ttl,
                       policy=PromotionPolicy(schedule_every_ticks=schedule, cluster_similarity=cluster))
    k = Kernel(cfg, similarity, PassthroughOracle(), clock=counting_clock())
    id2pat = {r.id: pattern_of(r) for r in records}
    buffered = 0
    for r in records:
        if k.ingest(r).outcome == "buffered":
            buffered += 1
        res = k.tick()
        if res.promotion and res.promotion.promoted:
            k.pin(k.snapshot())          # promoted memory stays visible, as in RepoPipeline.learn
    live = k.store.live()
    pure = sum(1 for m in live if len({id2pat[i] for i in m.provenance}) == 1)
    n = len(records)
    return {"theta": theta, "cluster": cluster, "candidates": n, "injected_redundant": expected_redundant(records) / n,
            "discard_rate": (n - buffered) / n, "promoted": len(live), "purity": pure / len(live) if live else None,
            "merged": (len(live) - pure) / len(live) if live else None}


def sweep(similarity, thetas, clusters, spec: StreamSpec, schedule: int = 10) -> list[dict]:
    memo = MemoSimilarity(similarity)
    records = generate(spec)                     # one stream, shared by every cell
    return [run_cell(memo, t, c, spec, schedule=schedule, records=records) for t in thetas for c in clusters]


def markdown(rows: list[dict], name: str) -> str:
    out = [f"# Threshold sweep — similarity: {name}", "",
           f"injected redundant fraction: {rows[0]['injected_redundant']:.3f}; candidates: {rows[0]['candidates']}", "",
           "| Θ_surprise | cluster_sim | discard_rate | promoted | purity | merged |", "|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        pu = "—" if r["purity"] is None else f"{r['purity']:.2f}"
        me = "—" if r["merged"] is None else f"{r['merged']:.2f}"
        out.append(f"| {r['theta']:.2f} | {r['cluster']:.2f} | {r['discard_rate']:.3f} | {r['promoted']} | {pu} | {me} |")
    return "\n".join(out) + "\n"


def recommend(rows: list[dict], tol: float = 0.05) -> dict | None:
    """Cells whose discard rate is within tol of the injected fraction and whose
    promoted memories are all pure; pick the one with the most promotions."""
    ok = [r for r in rows if abs(r["discard_rate"] - r["injected_redundant"]) <= tol and r["purity"] == 1.0 and r["promoted"] > 0]
    # closest to the injected fraction first, then most promotions, then the more conservative (higher) Θ
    return max(ok, key=lambda r: (-abs(r["discard_rate"] - r["injected_redundant"]), r["promoted"], r["theta"])) if ok else None


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--similarity", default="hashing", choices=["jaccard", "hashing", "embedding"])
    ap.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--embedding-revision", default=None)
    ap.add_argument("--thetas", default="0.15,0.2,0.25,0.3,0.35,0.4,0.5,0.6")
    ap.add_argument("--clusters", default="0.5,0.6,0.7,0.8,0.9")
    ap.add_argument("--mode", default="tokens", choices=["tokens", "nl"], help="nl = defect-like sentences with paraphrase (for semantic seams)")
    ap.add_argument("--n-records", type=int, default=300); ap.add_argument("--redundant", type=float, default=0.7); ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--schedule", type=int, default=10, help="promotion every N ticks (spec: on a schedule, not continuously)")
    ap.add_argument("--out", help="markdown path; a .json twin is written alongside")
    a = ap.parse_args(argv)
    sim = make_similarity(a.similarity, None, a.embedding_model, a.embedding_revision)
    spec = StreamSpec(mode=a.mode, n_records=a.n_records, n_patterns=a.n_records, redundant_fraction=a.redundant, seed=a.seed)
    rows = sweep(sim, [float(x) for x in a.thetas.split(",")], [float(x) for x in a.clusters.split(",")], spec, schedule=a.schedule)
    rec = recommend(rows)
    md = markdown(rows, getattr(sim, "name", a.similarity)) + "\nRecommended (discard within 0.05 of injected, purity 1.0, most promotions): " + (json.dumps(rec) if rec else "none") + "\n"
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(md)
        Path(a.out).with_suffix(".json").write_text(json.dumps({"similarity": getattr(sim, "name", a.similarity), "rows": rows, "recommended": rec}, indent=1))
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
