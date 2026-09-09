"""Synthetic event streams with known properties (Phase 1 is domain-free).

A stream has `n_patterns` latent defect patterns. Each record renders one
pattern as `signal_tokens` deterministic tokens plus `noise_tokens` random
tokens. With TokenJaccardSimilarity the same pattern scores >= s/(s+2n) and
different patterns score <= 2n/(2s+2n), so the surprise gate at theta=0.35
separates them cleanly for the default sizes (s=10, n=2).

`redundant_fraction` is the injected fraction of records that repeat an
already-seen pattern; the surprise gate should discard exactly those.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .canon import digest
from .records import Record
from .vclock import VectorClock


@dataclass(frozen=True)
class StreamSpec:
    n_records: int = 200
    n_patterns: int = 60
    redundant_fraction: float = 0.7
    bad_fraction: float = 1.0
    n_agents: int = 3
    signal_tokens: int = 10
    noise_tokens: int = 2
    noise_vocab: int = 50
    seed: int = 0
    wall_start: float = 1_700_000_000.0
    wall_step: float = 1.0
    distinct_inputs: bool = True   # each record from its own artifact


def pattern_text(pattern_id: int, signal_tokens: int = 10) -> str:
    return " ".join(f"p{pattern_id}t{i}" for i in range(signal_tokens))


def make_record(
    pattern_id: int,
    idx: int,
    *,
    label: str = "bad",
    agent_id: str = "agent-0",
    input_hash: str | None = None,
    noise: tuple[str, ...] = (),
    wall_clock: float = 0.0,
    vclock: VectorClock | None = None,
    signal_tokens: int = 10,
) -> Record:
    content = pattern_text(pattern_id, signal_tokens)
    if noise:
        content += " " + " ".join(noise)
    rid = digest({"pattern": pattern_id, "idx": idx, "content": content})
    return Record(
        id=rid,
        content=content,
        input_hash=input_hash or f"artifact-{idx}",
        agent_id=agent_id,
        vclock=vclock or VectorClock.of({agent_id: idx + 1}),
        wall_clock=wall_clock,
        label=label,
    )


def generate(spec: StreamSpec) -> list[Record]:
    if not 0.0 <= spec.redundant_fraction < 1.0:
        raise ValueError("redundant_fraction must be in [0,1)")
    rng = random.Random(spec.seed)
    n_unique = max(1, round(spec.n_records * (1.0 - spec.redundant_fraction)))
    n_unique = min(n_unique, spec.n_patterns, spec.n_records)
    patterns = list(range(n_unique))
    order = patterns + [rng.choice(patterns) for _ in range(spec.n_records - n_unique)]
    rng.shuffle(order)
    records: list[Record] = []
    for idx, pid in enumerate(order):
        noise = tuple(f"n{rng.randrange(spec.noise_vocab)}" for _ in range(spec.noise_tokens))
        label = "bad" if rng.random() < spec.bad_fraction else rng.choice(["good", "unknown"])
        agent = f"agent-{rng.randrange(spec.n_agents)}"
        records.append(
            make_record(
                pid,
                idx,
                label=label,
                agent_id=agent,
                input_hash=f"artifact-{idx}" if spec.distinct_inputs else f"artifact-{pid}",
                noise=noise,
                wall_clock=spec.wall_start + idx * spec.wall_step,
                signal_tokens=spec.signal_tokens,
            )
        )
    return records


def expected_redundant(records: list[Record]) -> int:
    """Number of records whose pattern was already seen earlier in the stream."""
    seen: set[str] = set()
    redundant = 0
    for r in records:
        key = r.content.split()[0]  # first signal token identifies the pattern
        if key in seen:
            redundant += 1
        seen.add(key)
    return redundant
