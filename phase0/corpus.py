"""Corpus ingestion: SWE-bench-Live -> corpus/tasks.jsonl, freshness-gated.

Sources (spec Phase 0, items 1-2, 5):
  - Hugging Face `SWE-bench-Live/SWE-bench-Live` (Python), splits lite | verified | full.
    `full` grows by ~50 verified issues per month; lite/verified are frozen.
  - A local JSONL/JSON export with the same fields (for offline runs).

Normalised task fields (superset of what Phase 0-4 need):
  instance_id, repo, base_commit, created_at, problem_statement, patch,
  test_patch, environment_setup_commit, hints_text, FAIL_TO_PASS, PASS_TO_PASS

The freshness gate is applied at import when a models.json is given, and
per-task verdicts are written next to the output for release (spec §5).

    python -m phase0.corpus pull  --split full --out corpus/tasks.jsonl [--models corpus/models.json]
    python -m phase0.corpus load  --input export.jsonl --out corpus/tasks.jsonl [--models ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .freshness_gate import filter_tasks

HF_DATASET = "SWE-bench-Live/SWE-bench-Live"
DOCKER_NAMESPACE = "starryzhang"   # per microsoft/SWE-bench-Live evaluation.py

REQUIRED = ("instance_id", "repo", "base_commit", "created_at", "problem_statement", "patch")


@dataclass(frozen=True)
class Task:
    instance_id: str
    repo: str
    base_commit: str
    created_at: str
    problem_statement: str
    patch: str
    test_patch: str = ""
    environment_setup_commit: str = ""
    hints_text: str = ""
    fail_to_pass: tuple[str, ...] = ()
    pass_to_pass: tuple[str, ...] = ()

    @property
    def docker_image(self) -> str:
        """Default per-task image name used by the SWE-bench-Live harness."""
        name = self.instance_id.replace("__", "_1776_").lower()
        return f"{DOCKER_NAMESPACE}/sweb.eval.x86_64.{name}"

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["fail_to_pass"] = list(self.fail_to_pass)
        d["pass_to_pass"] = list(self.pass_to_pass)
        return d


def _as_list(v: Any) -> tuple[str, ...]:
    if v is None or v == "":
        return ()
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return tuple(str(x) for x in parsed)
        except json.JSONDecodeError:
            return (v,)
        return (v,)
    return tuple(str(x) for x in v)


def normalise(raw: Mapping[str, Any]) -> Task:
    missing = [k for k in REQUIRED if not raw.get(k)]
    if missing:
        raise ValueError(f"task {raw.get('instance_id', '?')} missing {missing}")
    return Task(
        instance_id=str(raw["instance_id"]),
        repo=str(raw["repo"]),
        base_commit=str(raw["base_commit"]),
        created_at=str(raw["created_at"]),
        problem_statement=str(raw["problem_statement"]),
        patch=str(raw["patch"]),
        test_patch=str(raw.get("test_patch") or ""),
        environment_setup_commit=str(raw.get("environment_setup_commit") or ""),
        hints_text=str(raw.get("hints_text") or ""),
        fail_to_pass=_as_list(raw.get("FAIL_TO_PASS") or raw.get("fail_to_pass")),
        pass_to_pass=_as_list(raw.get("PASS_TO_PASS") or raw.get("pass_to_pass")),
    )


def read_tasks(path: str | Path) -> list[Task]:
    p = Path(path)
    text = p.read_text()
    if p.suffix == ".json":
        rows = json.loads(text)
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [normalise(r) for r in rows]


def write_tasks(tasks: Iterable[Task], path: str | Path) -> int:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w") as f:
        for t in tasks:
            f.write(json.dumps(t.to_json(), sort_keys=True) + "\n")
            n += 1
    return n


def pull_from_hf(dataset: str = HF_DATASET, split: str = "full") -> list[Task]:
    """`split="all"` concatenates every split of the dataset (de-duplicated by
    instance_id, first split wins) — for datasets whose split names are unknown."""
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise SystemExit("pip install datasets  (needs network access to huggingface.co)") from e
    if split != "all":
        return [normalise(row) for row in load_dataset(dataset, split=split)]
    seen: set[str] = set()
    out: list[Task] = []
    dd = load_dataset(dataset)
    for name in sorted(dd.keys()):
        sys.stderr.write(f"split {name}: {len(dd[name])} rows\n")
        for row in dd[name]:
            if row["instance_id"] in seen:
                continue
            seen.add(row["instance_id"])
            out.append(normalise(row))
    return out


def apply_freshness(tasks: list[Task], models_path: str | Path, report_path: str | Path | None, margin_days: int = 0) -> list[Task]:
    models = json.loads(Path(models_path).read_text())
    rows = [t.to_json() for t in tasks]
    accepted, rejected = filter_tasks(rows, models, margin_days)
    if report_path:
        rp = Path(report_path)
        rp.parent.mkdir(parents=True, exist_ok=True)
        with rp.open("w") as f:
            for _, v in accepted + rejected:
                f.write(json.dumps({"instance_id": v.instance_id, "created": str(v.created), "admitted": v.admitted, "reason": v.reason}) + "\n")
    sys.stderr.write(f"freshness gate: {len(accepted)} admitted, {len(rejected)} rejected\n")
    keep = {t["instance_id"] for t, _ in accepted}
    return [t for t in tasks if t.instance_id in keep]


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_pull = sub.add_parser("pull", help="download from Hugging Face")
    p_pull.add_argument("--dataset", default=HF_DATASET)
    p_pull.add_argument("--split", default="full")
    p_load = sub.add_parser("load", help="normalise a local JSON/JSONL export")
    p_load.add_argument("--input", required=True)
    for p in (p_pull, p_load):
        p.add_argument("--out", required=True)
        p.add_argument("--models", help="models.json {model_id: training cutoff}; applies the freshness gate")
        p.add_argument("--margin-days", type=int, default=0)
    args = ap.parse_args(argv)

    tasks = pull_from_hf(args.dataset, args.split) if args.cmd == "pull" else read_tasks(args.input)
    sys.stderr.write(f"loaded {len(tasks)} tasks\n")
    if args.models:
        report = Path(args.out).with_suffix(".freshness.jsonl")
        tasks = apply_freshness(tasks, args.models, report, args.margin_days)
    tasks.sort(key=lambda t: (t.repo, t.created_at, t.instance_id))
    n = write_tasks(tasks, args.out)
    sys.stderr.write(f"wrote {n} tasks -> {args.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
