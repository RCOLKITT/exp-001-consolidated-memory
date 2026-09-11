"""Phase 4 — evaluation: both arms on the eval split, interleaved, seeded.

    python -m phase4.evaluate --tasks corpus/tasks.jsonl --split corpus/split.json \
        --learn-dir runs/learn-001 --repos-dir corpus/repos --out runs/eval-001 --seed 7 \
        [--negative-control owner/name] [--model claude-opus-5]

Writes per-repo control/treatment flags + metrics and `gate4.json`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adapters.code.pipeline import ArmSpec, gate4_report, write_json
from memkernel.persist import load_kernel
from phase0.chains import build_chains
from phase0.corpus import apply_freshness, read_tasks
from phase0.metrics import ArmMetrics, lift
from phase3.learn import add_seam_args, make_pipeline


def _merge(ms: list[ArmMetrics]) -> ArmMetrics:
    per = {}
    for m in ms:
        per.update(m.per_repo)
    return ArmMetrics(sum(m.n_tasks for m in ms), sum(m.n_localized for m in ms), sum(m.n_flags for m in ms), sum(m.n_false_positive for m in ms), per)


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", required=True); ap.add_argument("--split", required=True); ap.add_argument("--learn-dir", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--models"); ap.add_argument("--repos-dir", default="corpus/repos"); ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--model", default="claude-opus-5"); ap.add_argument("--effort", default="high"); ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--provider", default="anthropic", choices=["anthropic", "openai-compatible"]); ap.add_argument("--base-url"); ap.add_argument("--api-key-env", default="MODEL_API_KEY"); ap.add_argument("--model-extra", default="")
    add_seam_args(ap)
    ap.add_argument("--ttl", type=int, default=30); ap.add_argument("--negative-control"); ap.add_argument("--cache"); ap.add_argument("--offline", action="store_true")
    ap.add_argument("--max-eval-per-repo", type=int, default=0, help="cap eval tasks per repo (smoke runs only)")
    ap.add_argument("--arms", default="control,treatment", help="arms to evaluate: control (no memory), treatment (frozen memory, gate τ = --tau), ungated (frozen memory, τ = 0)")
    args = ap.parse_args(argv)
    arm_names = [a.strip() for a in args.arms.split(",") if a.strip()]
    if "control" not in arm_names or "treatment" not in arm_names:
        ap.error("--arms must include control and treatment")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    tasks = read_tasks(args.tasks)
    if args.models:
        tasks = apply_freshness(tasks, args.models, out / "freshness.jsonl")
    split = json.loads(Path(args.split).read_text())
    controls, treatments, per_repo_lift, neg = [], [], {}, None
    secondary: dict[str, dict] = {n: {"control": [], "arm": [], "per_repo_lift": {}, "negative_control_lift": None} for n in arm_names if n not in ("control", "treatment")}
    file_level: dict[str, list] = {"control": [], "treatment": []}
    for chain in build_chains(tasks):
        if chain.repo not in split:
            continue
        _, ev = chain.split(int(split[chain.repo]))
        if args.max_eval_per_repo:
            ev = ev[: args.max_eval_per_repo]          # smoke runs only; never for the pre-registered evaluation
        rd = out / chain.repo.replace("/", "__")
        p = make_pipeline(chain.repo, chain.tasks, args, Path(args.cache) if args.cache else rd / "cache.jsonl")
        kpath = Path(args.learn_dir) / chain.repo.replace("/", "__") / "kernel.json"
        if chain.repo == args.negative_control or not kpath.exists():
            p.frozen_version = p.kernel.freeze()             # empty memory, still two arms
        else:
            load_kernel(kpath, p.kernel)
            p.frozen_version = p.kernel.pinned_version
        tau = {"control": 0.0, "treatment": args.tau, "ungated": 0.0}
        specs = [ArmSpec(n, None if n == "control" else p.frozen_version, tau.get(n, args.tau)) for n in arm_names]
        arms = p.evaluate_arms(ev, args.seed, specs)
        control, treatment = arms["control"], arms["treatment"]
        repo_of = {t.instance_id: chain.repo for t in ev}
        mc, mt = control.metrics(p.truth, repo_of), treatment.metrics(p.truth, repo_of)
        l = lift(mt, mc)
        flag_str = lambda f: f"{f.location.path}::{f.location.symbol}" if f.location.symbol else f.location.path
        arm_json = {}
        for name, a in arms.items():
            m = a.metrics(p.truth, repo_of)
            arm_json[name] = {"version": a.version, "tau": a.tau, "metrics": m.to_json(), "file_metrics": a.file_metrics(p.truth, repo_of).to_json(),
                              "flags": {k: [flag_str(f) for f in v] for k, v in a.flags_by_task.items()}, "hits": a.hits(p.truth),
                              "file_hits": {k: any(f.location.file_level.overlaps(h) for f in v for h in (p.truth.locations(k) or ())) for k, v in (a.file_flags_by_task or a.flags_by_task).items()},
                              "retrieved": a.retrieved_by_task, "scores": a.scores_by_task, "lift_vs_control": lift(m, mc)}
        write_json({"control": mc.to_json(), "treatment": mt.to_json(), "lift": l, "retrieval_hit_rate": treatment.retrieval_hit_rate,
                    "control_flags": {k: [f.location.path for f in v] for k, v in control.flags_by_task.items()},
                    "treatment_flags": {k: [f.location.path for f in v] for k, v in treatment.flags_by_task.items()},
                    "retrieved": treatment.retrieved_by_task, "errors": treatment.errors, "n_errors": len(treatment.errors),
                    "granularity": args.granularity, "arms": arm_json}, rd / "arms.json")
        if chain.repo == args.negative_control:
            neg = l
            for n in secondary:
                secondary[n]["negative_control_lift"] = arm_json[n]["lift_vs_control"]
        else:
            controls.append(mc); treatments.append(mt); per_repo_lift[chain.repo] = l
            file_level["control"].append(control.file_metrics(p.truth, repo_of)); file_level["treatment"].append(treatment.file_metrics(p.truth, repo_of))
            for n in secondary:
                secondary[n]["control"].append(mc); secondary[n]["arm"].append(arms[n].metrics(p.truth, repo_of)); secondary[n]["per_repo_lift"][chain.repo] = arm_json[n]["lift_vs_control"]
        sys.stderr.write(f"{chain.repo}: n={len(ev)} errors={len(treatment.errors)} control loc={mc.localization_rate:.3f} fp={mc.false_positive_rate:.3f} | treatment loc={mt.localization_rate:.3f} fp={mt.false_positive_rate:.3f} | lift={l}\n")
    report = gate4_report(_merge(controls), _merge(treatments), per_repo_lift, neg) if controls else {"error": "no repos evaluated"}
    if controls:
        report["granularity"] = args.granularity; report["tau"] = args.tau; report["arms"] = arm_names
        report["secondary_arms"] = {n: gate4_report(_merge(d["control"]), _merge(d["arm"]), d["per_repo_lift"], d["negative_control_lift"]) for n, d in secondary.items()}
        if args.granularity == "function":
            fc, ft = _merge(file_level["control"]), _merge(file_level["treatment"])
            report["file_level_secondary"] = {"control": fc.to_json(), "treatment": ft.to_json(), **lift(ft, fc)}
    write_json(report, out / "gate4.json")
    sys.stdout.write(json.dumps({k: report[k] for k in report if k not in ("control", "treatment")}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
