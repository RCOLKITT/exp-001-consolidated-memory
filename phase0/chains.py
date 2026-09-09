"""Per-repository chronological chains and the corpus decision (spec Phase 0
item 5, Phase 2 items 2-3).

A chain is every task of one repo ordered by created_at. Memory accumulates
along a chain, so chain length is the resource that decides ChainSWE vs
SWE-bench-Live and whether Gate 2's power requirement can be met.

    python -m phase0.chains corpus/tasks.jsonl [--min-build N] [--min-eval M] [--md report.md]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Sequence

from .corpus import Task, read_tasks
from .freshness_gate import _parse_date


@dataclass(frozen=True)
class Chain:
    repo: str
    tasks: tuple[Task, ...]          # chronological

    def __len__(self) -> int:
        return len(self.tasks)

    @property
    def first(self) -> date | None:
        return _parse_date(self.tasks[0].created_at)

    @property
    def last(self) -> date | None:
        return _parse_date(self.tasks[-1].created_at)

    @property
    def span_days(self) -> int:
        f, l = self.first, self.last
        return (l - f).days if f and l else 0

    def split(self, n_build: int) -> tuple[tuple[Task, ...], tuple[Task, ...]]:
        """Chronological split: positions 1..n_build build memory, rest evaluate.
        Never random (spec §8, temporal leakage)."""
        return self.tasks[:n_build], self.tasks[n_build:]


def build_chains(tasks: Sequence[Task]) -> list[Chain]:
    by_repo: dict[str, list[Task]] = {}
    for t in tasks:
        by_repo.setdefault(t.repo, []).append(t)
    chains = []
    for repo, ts in by_repo.items():
        ts.sort(key=lambda t: (t.created_at, t.instance_id))
        chains.append(Chain(repo, tuple(ts)))
    chains.sort(key=lambda c: (-len(c), c.repo))
    return chains


@dataclass(frozen=True)
class ChainStats:
    n_repos: int
    n_tasks: int
    lengths: tuple[int, ...]
    eligible_repos: tuple[str, ...]    # len >= min_build + min_eval

    @property
    def median_length(self) -> float:
        return statistics.median(self.lengths) if self.lengths else 0.0

    def count_at_least(self, k: int) -> int:
        return sum(1 for n in self.lengths if n >= k)


def stats(chains: Sequence[Chain], min_build: int, min_eval: int) -> ChainStats:
    lengths = tuple(len(c) for c in chains)
    eligible = tuple(c.repo for c in chains if len(c) >= min_build + min_eval)
    return ChainStats(len(chains), sum(lengths), lengths, eligible)


def markdown_report(chains: Sequence[Chain], min_build: int, min_eval: int, top: int = 30) -> str:
    s = stats(chains, min_build, min_eval)
    lines = [
        "# Chain report",
        "",
        f"- repos: {s.n_repos}, tasks: {s.n_tasks}, median chain length: {s.median_length:g}",
        f"- repos with >= 5 tasks: {s.count_at_least(5)}; >= 10: {s.count_at_least(10)}; >= 20: {s.count_at_least(20)}; >= 40: {s.count_at_least(40)}",
        f"- eligible for build/eval split (>= {min_build} build + {min_eval} eval): {len(s.eligible_repos)}",
        "",
        "| repo | tasks | first | last | span (days) | eligible |",
        "|---|---:|---|---|---:|---|",
    ]
    for c in chains[:top]:
        ok = "yes" if len(c) >= min_build + min_eval else ""
        lines.append(f"| {c.repo} | {len(c)} | {c.first} | {c.last} | {c.span_days} | {ok} |")
    if len(chains) > top:
        lines.append(f"| … {len(chains) - top} more repos | | | | | |")
    return "\n".join(lines) + "\n"


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks_jsonl")
    ap.add_argument("--min-build", type=int, default=20, help="min build-split tasks per repo (Gate 2 power floor; set at pre-registration)")
    ap.add_argument("--min-eval", type=int, default=10, help="min eval-split tasks per repo")
    ap.add_argument("--md", help="write a markdown report here")
    ap.add_argument("--json", dest="json_out", help="write per-repo JSON here")
    args = ap.parse_args(argv)
    chains = build_chains(read_tasks(args.tasks_jsonl))
    report = markdown_report(chains, args.min_build, args.min_eval)
    if args.md:
        Path(args.md).write_text(report)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            [{"repo": c.repo, "n": len(c), "first": str(c.first), "last": str(c.last), "span_days": c.span_days,
              "instance_ids": [t.instance_id for t in c.tasks]} for c in chains], indent=1))
    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
