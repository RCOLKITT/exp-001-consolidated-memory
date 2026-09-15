# Product lesson: the rank is the signal

*What three registered experiments on defect-localization memory actually
taught us, and what to build with it. 2026-09-15.*

## The lesson in one paragraph

When the verifier names three places a bug might live, its **first** guess
is right about half the time and its **second and third** guesses are
wrong about six times in seven. That ordering is the only reliable signal
we found in this whole program. Memory of past defects did not move the
needle (v1 +1.1 pts, v2 −1.3 pts, both indistinguishable from placebo),
and a veto memory of past mistakes barely beat "drop a low-ranked guess at
random". The product decision is therefore not *what the system
remembers* but *how it presents its ranked guesses*, and that decision
hinges on one number we have not measured yet: what a wrong pointer costs
a developer relative to a right one.

## What the data show

Precision by rank, i.e. how often the guess at that position is correct.
File level is the v1 verifier on the ten development repositories (378
tasks); function level is the v2 registered run (526 tasks). Same model
(Llama 3.3 70B), same corpus (SWE-bench-Live Python, 2024–2025 issues).

| rank | file level | function level |
|---|---:|---:|
| 1st guess | **0.49** | **0.37** |
| 2nd guess | 0.15 | 0.22 |
| 3rd guess | 0.13 | 0.17 |

The drop is monotone in every repository we have (rank-2/3 precision at
file level ranges 0.07 to 0.25 across the eleven repos). The verifier's
own ordering is informative; the three pointers are not peers.

What each display policy delivers, per task:

| policy | file: hit rate | file: wrong pointers | function: hit rate | function: wrong pointers |
|---|---:|---:|---:|---:|
| show 1 | 0.48 | 0.51 | 0.37 | 0.61 |
| show 2 | 0.59 | 1.32 | 0.46 | 1.31 |
| show 3 | 0.66 | 2.06 | 0.49 | 1.95 |

Showing three instead of one raises the chance the right place is on
screen by 17 points (file) or 12 (function), and costs 1.5 extra wrong
pointers per task to get it. The second and third guesses are lottery
tickets, and they do pay out: 10% of tasks are rescued only by the second
guess and 7% only by the third (file level).

## The trade, made explicit

Let a right pointer be worth 1 and a wrong pointer cost *c* (in the same
units: minutes of a developer's attention, trust, whatever the product's
currency is). Expected value per task is *hits − c × wrong*. From the
table:

- file level: show-1 beats show-3 when *c* > 0.11; show-2 beats show-3 when *c* > 0.10;
- function level: show-1 beats show-3 when *c* > 0.09.

So the whole decision turns on whether a wrong pointer costs a developer
more than about a tenth of what a right one saves. Nobody in this program
has measured *c*. That measurement is worth more than any further memory
experiment.

## Why this beats memory

- **v1** (file-level memory of prior defects, 371 paired tasks): +1.1 pts, CI −2.0 to +4.2.
- **v2** (function-level memory, prequential, 526 paired tasks): −1.3 pts, CI −3.3 to +0.6; a placebo arm injecting *irrelevant* memories did the same (−0.8). The verifier reacts to the memory section's presence, not its content.
- **veto memory** (drafted, not run): removing files the verifier has blamed wrongly twice cuts false positives 2.1 pts, but removing the same number of low-ranked flags *at random* cuts them 1.7 pts. The memory's own contribution is 0.4 pts, inside the noise of any pool the corpus offers.

Every one of those mechanisms was trying to add information the verifier
would then have to use correctly. The rank needs no such cooperation: it
is already in the output, and it is honest.

## What to build

1. **Tier the pointers.** One "best guess" and, visually subordinate, "also
   possible". Never three equal rows. The order is the product's single
   most trustworthy claim; make the interface say so.
2. **Calibrate the language to the rank.** "About 1 in 2" for the first
   guess, "about 1 in 7" for the others, using this verifier's measured
   rates; re-measure per verifier, since rates will differ by model. A
   number the user can check beats an adjective.
3. **Measure *c*.** Instrument which pointer a developer opens first, how
   long a wrong one costs them, and whether they come back. A week of
   that data settles show-1 versus show-3 better than any experiment here.
4. **Let the user choose the tier count**, defaulting to the policy that
   the measured *c* favours. The lottery tickets are worth showing to some
   users and not to others.
5. **Log the rank of every accepted pointer.** It is the cheapest ongoing
   check that the ordering stays informative when the verifier changes.

What not to build yet: defect memory (v1, v2), veto memory (v3 draft),
or a "confidence from agreement" heuristic — at file level the three
guesses agreeing on a directory tells you nothing about the first guess
(precision 0.44 to 0.49 either way); at function level it is a weak
signal (0.27 when the guesses scatter across directories, 0.39 when they
share one), not enough to ship.

## Caveats

One verifier, one language, one corpus. The *shape* (a steep, monotone
drop after the first guess) is what we expect to generalise; the *rates*
will move with the model and with how a product asks the question. Any
stronger model should be re-measured with the same three-line analysis
before its rates are shown to users. The file-level rows use the ten
development repositories from v1; the function-level rows are the
registered v2 run, sharded and merged with a config check.

## Evidence trail (repository `RCOLKITT/exp-001-consolidated-memory`)

- rank and policy numbers: `docs/PRODUCT-LESSON-rank.md` (this file) reproduced from `results/phase0/18/control/flags.jsonl`, `results/experiment/6/eval/*.arms.json` (file level) and `results/experiment/{18,19,20}/rolling/*.arms.json` (function level, with per-task gold keys)
- v1 result: `docs/phase0-findings.md` §15, `results/experiment/7/paired/`
- v2 result: `docs/phase0-findings.md` §20, `results/experiment/21/`
- veto simulation and placebo: `docs/phase0-findings.md` §21–22, `phase4/veto_sim.py`, `docs/PREREGISTRATION-v3-DRAFT.md`
