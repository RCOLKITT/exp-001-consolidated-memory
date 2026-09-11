"""Shared result assembly for phase4.evaluate (one split) and phase4.rolling
(prequential): per-repo arms.json and the aggregate gate4.json."""
from __future__ import annotations

from typing import Optional

from adapters.code.pipeline import ArmResult, gate4_report
from phase0.metrics import ArmMetrics, lift


def merge(ms: list[ArmMetrics]) -> ArmMetrics:
    per = {}
    for m in ms:
        per.update(m.per_repo)
    return ArmMetrics(sum(m.n_tasks for m in ms), sum(m.n_localized for m in ms), sum(m.n_flags for m in ms), sum(m.n_false_positive for m in ms), per)


def flag_str(f) -> str:
    return f"{f.location.path}::{f.location.symbol}" if f.location.symbol else f.location.path


def arms_json(arms: dict[str, ArmResult], truth, repo_of: dict, granularity: str, extra: Optional[dict] = None) -> dict:
    control, treatment = arms["control"], arms["treatment"]
    mc, mt = control.metrics(truth, repo_of), treatment.metrics(truth, repo_of)
    per_arm = {}
    for name, a in arms.items():
        m = a.metrics(truth, repo_of)
        per_arm[name] = {"version": a.version, "tau": a.tau, "metrics": m.to_json(), "file_metrics": a.file_metrics(truth, repo_of).to_json(),
                         "flags": {k: [flag_str(f) for f in v] for k, v in a.flags_by_task.items()}, "hits": a.hits(truth),
                         "file_hits": {k: any(f.location.file_level.overlaps(h) for f in v for h in (truth.locations(k) or ())) for k, v in (a.file_flags_by_task or a.flags_by_task).items()},
                         "retrieved": a.retrieved_by_task, "scores": a.scores_by_task, "lift_vs_control": lift(m, mc),
                         **({"versions": a.version_by_task} if a.version_by_task else {})}
    return {"control": mc.to_json(), "treatment": mt.to_json(), "lift": lift(mt, mc), "retrieval_hit_rate": treatment.retrieval_hit_rate,
            "control_flags": {k: [f.location.path for f in v] for k, v in control.flags_by_task.items()},
            "treatment_flags": {k: [f.location.path for f in v] for k, v in treatment.flags_by_task.items()},
            "retrieved": treatment.retrieved_by_task, "errors": treatment.errors, "n_errors": len(treatment.errors),
            "granularity": granularity, "arms": per_arm, **(extra or {})}


class Aggregator:
    """Collects per-repo metrics across repos and emits gate4.json."""

    def __init__(self, arm_names: list[str], granularity: str, tau: float) -> None:
        self.arm_names, self.granularity, self.tau = arm_names, granularity, tau
        self.controls, self.treatments, self.per_repo_lift, self.neg = [], [], {}, None
        self.secondary = {n: {"control": [], "arm": [], "per_repo_lift": {}, "negative_control_lift": None} for n in arm_names if n not in ("control", "treatment")}
        self.file_level = {"control": [], "treatment": []}

    def add(self, repo: str, arms: dict[str, ArmResult], truth, repo_of: dict, aj: dict, is_negative_control: bool) -> None:
        mc, mt = arms["control"].metrics(truth, repo_of), arms["treatment"].metrics(truth, repo_of)
        if is_negative_control:
            self.neg = aj["lift"]
            for n in self.secondary:
                self.secondary[n]["negative_control_lift"] = aj["arms"][n]["lift_vs_control"]
            return
        self.controls.append(mc); self.treatments.append(mt); self.per_repo_lift[repo] = aj["lift"]
        self.file_level["control"].append(arms["control"].file_metrics(truth, repo_of)); self.file_level["treatment"].append(arms["treatment"].file_metrics(truth, repo_of))
        for n in self.secondary:
            self.secondary[n]["control"].append(mc); self.secondary[n]["arm"].append(arms[n].metrics(truth, repo_of)); self.secondary[n]["per_repo_lift"][repo] = aj["arms"][n]["lift_vs_control"]

    def report(self, extra: Optional[dict] = None) -> dict:
        if not self.controls:
            return {"error": "no repos evaluated"}
        rep = gate4_report(merge(self.controls), merge(self.treatments), self.per_repo_lift, self.neg)
        rep["granularity"] = self.granularity; rep["tau"] = self.tau; rep["arms"] = self.arm_names
        rep["secondary_arms"] = {n: gate4_report(merge(d["control"]), merge(d["arm"]), d["per_repo_lift"], d["negative_control_lift"]) for n, d in self.secondary.items()}
        if self.granularity == "function":
            fc, ft = merge(self.file_level["control"]), merge(self.file_level["treatment"])
            rep["file_level_secondary"] = {"control": fc.to_json(), "treatment": ft.to_json(), **lift(ft, fc)}
        rep.update(extra or {})
        return rep
