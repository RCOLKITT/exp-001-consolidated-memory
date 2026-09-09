# Belief provenance under clock skew

**Claim:** in a multi-agent system, "did agent B know memory M when it acted?"
cannot be answered from timestamps. It can be answered from causal order.

This is the mechanism assertion behind Gate 1 and the durable contribution
of EXP-001 regardless of what Phases 3–4 find (spec, Phase 1 note).

## Setup

Three agents. Each stamps its records with its own wall clock and with a
vector clock that it merges whenever it reads another agent's output.

| Step | Agent | Wall clock | Vector clock | Event |
|---|---|---|---|---|
| 1 | A | 1000 | `{A:1}` | promotes memory **M** |
| 2 | B | **885** (clock 120 s slow) | `{A:1, B:1}` | reads M, then produces action **R_B** |
| 3 | C | **1125** (clock 120 s fast) | `{C:1}` | never reads M, produces action **R_C** |

B's vector clock carries `A:1` because B merged A's clock when it read M.
C's does not.

## Question: did the agent know M when it acted?

| Method | R_B (did know) | R_C (did not know) |
|---|---|---|
| Wall clock: `action.t >= M.t` | 885 ≥ 1000 → **No (wrong)** | 1125 ≥ 1000 → **Yes (wrong)** |
| Causal: `M.vclock <= action.vclock` | `{A:1} <= {A:1,B:1}` → **Yes (right)** | `{A:1} <= {C:1}` false → **No (right)** |

Wall-clock ordering is wrong in both directions: a false negative (it
exonerates B, who acted on M) and a false positive (it implicates C, who
never saw M). Causal ordering is right in both, and it is right *without
knowing anything about the skew*.

## Why this matters for the ledger

If provenance were timestamp-based, a skewed clock could make a promoted
memory appear to predate the evidence that produced it, or make an agent's
action appear uninformed by memory it demonstrably retrieved. Either breaks
the thesis' second clause — *every belief it acquired is traceable to the
evidence that produced it*. The kernel therefore:

1. puts a vector clock on every record, memory object, and ledger entry;
2. merges the clock on every read (`Kernel.ingest` merges `record.vclock`);
3. excludes wall clock from every hash (docs/DECISIONS.md, D3);
4. answers provenance questions only with `memkernel.provenance.knew_by_causal_order`.

`knew_by_wall_clock` is kept in the codebase for one purpose: to be shown
wrong by `tests/test_clock_skew.py`.

## Reproduce

```
python -m pytest -v tests/test_clock_skew.py
```

The demonstration uses fixed constants and no randomness. It is reproducible
by construction; the test runs it three times in a row to make the point.

## Limits

- Vector clocks grow with the number of agents. For EXP-001 the agent count
  is single digits; not a concern here, noted for the spec.
- Causal order says what an agent *could* have known (M was in its causal
  past). Whether it *used* M is a retrieval question, answered by the
  ledger's `retrieve` entries, not by the clock.
