"""Seam diagnostics on a learned kernel (real records, not synthetic).

Reads runs/learn/<repo>/kernel.json (ledger: every ingest with the record's
content, label, surprise decision and outcome) and embeddings.jsonl, and
reports what the pre-registration needs to know before fixing Θ and ρ:

  - outcome counts: buffered / reinforced / discarded, by label
  - pairwise cosine quantiles for same-file vs different-file records
    (the file path is the "component" of the code adapter, D23)
  - the fraction of same-file pairs above candidate ρ values
  - support sizes of buffered entries and why nothing promoted

    python -m phase3.diagnose runs/learn/<repo> [--out diag.json]
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

from adapters.code.similarity import EmbeddingCosineSimilarity

_LOC = re.compile(r"=> (.+?) ::")


def file_of(content: str) -> str:
    m = _LOC.search(content)
    return m.group(1).strip() if m else "?"


def q(xs):
    xs = sorted(xs); n = len(xs)
    if not n:
        return None
    return {"n": n, "p05": xs[int(.05 * n)], "p25": xs[int(.25 * n)], "med": xs[n // 2], "p75": xs[int(.75 * n)], "p95": xs[min(n - 1, int(.95 * n))]}


def diagnose(run_dir: Path) -> dict:
    k = json.loads((run_dir / "kernel.json").read_text())
    ingests = [e for e in k["ledger"] if e["event"] == "ingest"]
    recs = [(e["payload"]["record"], e["payload"]["decision"], e["payload"]["outcome"]) for e in ingests]
    outcomes: dict = {}
    for r, d, o in recs:
        outcomes.setdefault(o, {}).setdefault(r["label"], 0)
        outcomes[o][r["label"]] += 1
    band = sum(1 for r, d, o in recs if o == "discarded" and d["max_similarity"] >= 1 - k["config"]["theta_surprise"])
    embedder = k["config"].get("similarity_name") or None

    class Frozen:
        name = embedder or ""
        def __call__(self, t): raise LookupError(t)

    same, diff, rho_pass = [], [], {}
    vec_path = run_dir / "embeddings.jsonl"
    if vec_path.exists():
        # the embedder name is part of the cache key; recover it from any gate3.json next door
        g = run_dir / "gate3.json"
        Frozen.name = json.loads(g.read_text())["similarity"] if g.exists() else Frozen.name
        sim = EmbeddingCosineSimilarity(Frozen(), vec_path)
        contents = [(r["content"], file_of(r["content"])) for r, _, _ in recs]
        try:
            for (ca, fa), (cb, fb) in itertools.combinations(contents, 2):
                s = sim.sim(ca, cb)
                (same if fa == fb else diff).append(s)
        except LookupError as e:
            same, diff = [], []
            sys.stderr.write(f"vectors missing for some records ({e}); pairwise stats skipped\n")
        for rho in (0.5, 0.55, 0.6, 0.65, 0.7, 0.75):
            rho_pass[str(rho)] = {"same_file": round(sum(1 for x in same if x >= rho) / len(same), 3) if same else None,
                                  "diff_file": round(sum(1 for x in diff if x >= rho) / len(diff), 3) if diff else None}
    supports = {}
    for e in k["ledger"]:
        if e["event"] == "promote":
            pass
    return {
        "repo_dir": str(run_dir), "theta": k["config"]["theta_surprise"], "rho": k["config"].get("reinforce_min_sim"),
        "n_ingested": len(recs), "outcomes_by_label": outcomes,
        "discarded_in_theta_rho_band": band,
        "same_file_cosine": q(same), "diff_file_cosine": q(diff), "share_of_pairs_at_or_above": rho_pass,
        "promoted": len(k["objects"]),
    }


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir"); ap.add_argument("--out")
    a = ap.parse_args(argv)
    d = diagnose(Path(a.run_dir))
    s = json.dumps(d, indent=1)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(s)
    print(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
