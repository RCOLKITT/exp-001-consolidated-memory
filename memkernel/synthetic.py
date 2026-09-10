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
    mode: str = "tokens"           # "tokens": opaque signal tokens (lexical seams); "nl": defect-like sentences (semantic seams)
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


# ---------------------------------------------------------------------------
# Natural-language mode: a pattern is (component, symptom); each record is a
# paraphrase of it. Same pattern => semantically close; different pattern =>
# different meaning. This is what a sentence embedder can be tuned on.
# ---------------------------------------------------------------------------
_COMPONENTS = [
    ["csv parser", "the CSV reader", "csv loading code"], ["http client", "the request layer", "outbound HTTP wrapper"],
    ["config loader", "settings parser", "the configuration reader"], ["cli argument parser", "command-line option handling", "the argparse layer"],
    ["retry wrapper", "the backoff helper", "retry decorator"], ["date formatter", "timestamp rendering", "the datetime helper"],
    ["cache layer", "the memoization cache", "result cache"], ["auth middleware", "the login check", "session validation"],
    ["file watcher", "the inotify handler", "filesystem polling"], ["json serializer", "the JSON encoder", "response serialization"],
    ["plugin loader", "extension discovery", "the entry-point scanner"], ["thread pool", "the worker executor", "background job runner"],
    ["template renderer", "the jinja layer", "page rendering"], ["unicode normalizer", "text normalisation", "the encoding shim"],
    ["dependency resolver", "version solving", "the lockfile resolver"], ["log formatter", "the logging handler", "structured log output"],
    ["pagination helper", "the cursor iterator", "page splitting"], ["schema validator", "input validation", "the pydantic models"],
    ["image resizer", "thumbnail generation", "the PIL wrapper"], ["websocket handler", "the socket loop", "realtime channel code"],
    ["sql query builder", "the ORM layer", "statement composition"], ["yaml loader", "the YAML reader", "manifest parsing"],
    ["rate limiter", "the throttle", "request quota logic"], ["path resolver", "relative path handling", "the filesystem path helper"],
    ["env var reader", "environment parsing", "the dotenv loader"], ["signal handler", "shutdown hooks", "the SIGTERM path"],
    ["metrics exporter", "the prometheus endpoint", "stats reporting"], ["diff generator", "patch rendering", "the unified-diff writer"],
    ["tokenizer", "the lexer", "token splitting"], ["scheduler", "the cron runner", "job timing logic"],
]
_SYMPTOMS = [
    ["drops the last row", "loses the final record", "truncates the trailing entry"], ["is off by one", "miscounts by a single element", "has an off-by-one boundary error"],
    ["returns None instead of an empty list", "yields null where an empty collection is expected", "gives None for no results"],
    ["leaks a file handle", "never closes the file", "keeps the descriptor open"], ["ignores the timezone", "treats naive and aware datetimes alike", "discards tz info"],
    ["double-encodes utf-8", "encodes text twice", "produces mojibake on non-ascii"], ["crashes on an empty input", "raises on zero-length data", "fails when given nothing"],
    ["silently swallows exceptions", "hides errors", "catches and ignores failures"], ["races under concurrent calls", "is not thread-safe", "corrupts state when called in parallel"],
    ["mishandles windows paths", "breaks on backslash separators", "fails with drive-letter paths"], ["retries forever", "never gives up on failure", "loops without a retry cap"],
    ["caches stale results", "serves outdated values", "does not invalidate on change"], ["mutates its input", "modifies the caller's argument", "has a side effect on the passed object"],
    ["misparses quoted values", "breaks on embedded quotes", "splits inside quotation marks"], ["overflows on large files", "runs out of memory on big inputs", "loads everything into RAM"],
]
_PREFIX = ["", "", "bug:", "issue:", "regression:", "found that", "it looks like"]
_SUFFIX = ["", "", "when the input is empty", "under load", "on windows", "after upgrading", "in the nightly build", "only in CI", "with unicode names", "since the refactor"]
PATTERN_OF: dict[str, str] = {}   # record id -> pattern key, filled by generate(); see pattern_of()


def nl_pattern_key(pattern_id: int) -> str:
    c = pattern_id % len(_COMPONENTS)
    s = (pattern_id // len(_COMPONENTS)) % len(_SYMPTOMS)
    return f"c{c}s{s}"


def nl_text(pattern_id: int, rng: random.Random) -> str:
    c = pattern_id % len(_COMPONENTS)
    s = (pattern_id // len(_COMPONENTS)) % len(_SYMPTOMS)
    comp = rng.choice(_COMPONENTS[c]); sym = rng.choice(_SYMPTOMS[s])
    pre = rng.choice(_PREFIX); suf = rng.choice(_SUFFIX)
    core = f"{comp} {sym}" if rng.random() < 0.7 else f"{sym[0].upper() + sym[1:]} in {comp}"
    return " ".join(x for x in (pre, core, suf) if x).strip()


def pattern_of(record: Record) -> str:
    """Pattern key of a synthetic record: registry for nl mode, first signal token otherwise."""
    return PATTERN_OF.get(record.id) or record.content.split()[0]


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
    if spec.mode == "nl" and n_unique > len(_COMPONENTS) * len(_SYMPTOMS):
        raise ValueError(f"nl mode supports at most {len(_COMPONENTS) * len(_SYMPTOMS)} distinct patterns")
    records: list[Record] = []
    for idx, pid in enumerate(order):
        label = "bad" if rng.random() < spec.bad_fraction else rng.choice(["good", "unknown"])
        agent = f"agent-{rng.randrange(spec.n_agents)}"
        input_hash = f"artifact-{idx}" if spec.distinct_inputs else f"artifact-{pid}"
        wall = spec.wall_start + idx * spec.wall_step
        if spec.mode == "nl":
            content = nl_text(pid, rng)
            rid = digest({"pattern": pid, "idx": idx, "content": content, "mode": "nl"})
            r = Record(id=rid, content=content, input_hash=input_hash, agent_id=agent,
                       vclock=VectorClock.of({agent: idx + 1}), wall_clock=wall, label=label)
            PATTERN_OF[rid] = nl_pattern_key(pid)
        else:
            noise = tuple(f"n{rng.randrange(spec.noise_vocab)}" for _ in range(spec.noise_tokens))
            r = make_record(pid, idx, label=label, agent_id=agent, input_hash=input_hash, noise=noise,
                            wall_clock=wall, signal_tokens=spec.signal_tokens)
        records.append(r)
    return records


def expected_redundant(records: list[Record]) -> int:
    """Number of records whose pattern was already seen earlier in the stream."""
    seen: set[str] = set()
    redundant = 0
    for r in records:
        key = pattern_of(r)
        if key in seen:
            redundant += 1
        seen.add(key)
    return redundant
