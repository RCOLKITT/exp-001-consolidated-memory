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


def component_of(key: str) -> str:
    return key.split("s")[0] if key.startswith("c") else key


def run_cell(similarity, theta: float, cluster: float, spec: StreamSpec, ttl: int = 10_000, schedule: int = 10, records=None, rho=None) -> dict:
    records = records if records is not None else generate(spec)
    cfg = KernelConfig(theta_surprise=theta, reinforce_min_sim=rho, ttl_ticks=ttl,
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
    pure_c = sum(1 for m in live if len({component_of(id2pat[i]) for i in m.provenance}) == 1)
    reinforced = sum(1 for e in k.ledger.events("ingest") if e.payload["outcome"] == "reinforced")
    n = len(records)
    return {"theta": theta, "rho": rho, "cluster": cluster, "candidates": n, "injected_redundant": expected_redundant(records) / n,
            "discard_rate": (n - buffered) / n, "reinforced": reinforced, "promoted": len(live),
            "purity": pure / len(live) if live else None, "purity_component": pure_c / len(live) if live else None,
            "merged": (len(live) - pure) / len(live) if live else None}


def sweep(similarity, thetas, clusters, spec: StreamSpec, schedule: int = 10, rhos=(None,)) -> list[dict]:
    memo = MemoSimilarity(similarity)
    records = generate(spec)                     # one stream, shared by every cell
    return [run_cell(memo, t, c, spec, schedule=schedule, records=records, rho=r) for t in thetas for r in rhos for c in clusters]


def markdown(rows: list[dict], name: str) -> str:
    out = [f"# Threshold sweep — similarity: {name}", "",
           f"injected redundant fraction: {rows[0]['injected_redundant']:.3f}; candidates: {rows[0]['candidates']}", "",
           "| Θ_surprise | ρ_reinforce | cluster_sim | discard_rate | reinforced | promoted | purity (pattern) | purity (component) |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        pu = "—" if r["purity"] is None else f"{r['purity']:.2f}"
        pc = "—" if r.get("purity_component") is None else f"{r['purity_component']:.2f}"
        rho = "1-Θ" if r.get("rho") is None else f"{r['rho']:.2f}"
        out.append(f"| {r['theta']:.2f} | {rho} | {r['cluster']:.2f} | {r['discard_rate']:.3f} | {r.get('reinforced', 0)} | {r['promoted']} | {pu} | {pc} |")
    return "\n".join(out) + "\n"


def recommend(rows: list[dict], tol: float = 0.05, min_purity: float = 1.0, level: str = "purity") -> dict | None:
    """Cells whose discard rate is within tol of the injected fraction and whose
    promoted memories reach min_purity at `level` (purity | purity_component);
    pick the one with the most promotions."""
    ok = [r for r in rows if abs(r["discard_rate"] - r["injected_redundant"]) <= tol and (r.get(level) or 0) >= min_purity and r["promoted"] > 0]
    # closest to the injected fraction first, then most promotions, then the more conservative (higher) Θ
    return max(ok, key=lambda r: (-abs(r["discard_rate"] - r["injected_redundant"]), r["promoted"], r["theta"])) if ok else None


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--similarity", default="hashing", choices=["jaccard", "hashing", "embedding"])
    ap.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--embedding-revision", default=None)
    ap.add_argument("--thetas", default="0.15,0.2,0.25,0.3,0.35,0.4,0.5,0.6")
    ap.add_argument("--rhos", default="", help="reinforcement thresholds to sweep, e.g. 0.6,0.7,0.8,0.9 (blank = 1-Θ only)")
    ap.add_argument("--embedding-cache", default=None, help="persist vectors here (commit it to analyse offline)")
    ap.add_argument("--clusters", default="0.5,0.6,0.7,0.8,0.9")
    ap.add_argument("--mode", default="tokens", choices=["tokens", "nl"], help="nl = defect-like sentences with paraphrase (for semantic seams)")
    ap.add_argument("--n-records", type=int, default=300); ap.add_argument("--redundant", type=float, default=0.7); ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--schedule", type=int, default=10, help="promotion every N ticks (spec: on a schedule, not continuously)")
    ap.add_argument("--out", help="markdown path; a .json twin is written alongside")
    a = ap.parse_args(argv)
    sim = make_similarity(a.similarity, a.embedding_cache, a.embedding_model, a.embedding_revision)
    spec = StreamSpec(mode=a.mode, n_records=a.n_records, n_patterns=a.n_records, redundant_fraction=a.redundant, seed=a.seed)
    rhos = [None] + [float(x) for x in a.rhos.split(",") if x]
    rows = sweep(sim, [float(x) for x in a.thetas.split(",")], [float(x) for x in a.clusters.split(",")], spec, schedule=a.schedule, rhos=rhos)
    rec = recommend(rows)
    rec_c = recommend(rows, min_purity=0.95, level="purity_component")
    md = (markdown(rows, getattr(sim, "name", a.similarity))
          + "\nRecommended, pattern purity 1.0 (discard within 0.05 of injected, most promotions): " + (json.dumps(rec) if rec else "none")
          + "\nRecommended, component purity >= 0.95: " + (json.dumps(rec_c) if rec_c else "none") + "\n")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(md)
        Path(a.out).with_suffix(".json").write_text(json.dumps({"similarity": getattr(sim, "name", a.similarity), "rows": rows, "recommended": rec, "recommended_component": rec_c}, indent=1))
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
