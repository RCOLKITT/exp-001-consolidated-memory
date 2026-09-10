"""Promotion policy constants for the code adapter (spec §6). Hand-set; no
adaptive thresholds (spec §1). Changing these after pre-registration
invalidates the result (spec §7)."""
from memkernel import PromotionPolicy

# Tuned on natural-language synthetic streams with the pinned embedding seam
# (sentence-transformers/all-MiniLM-L6-v2 @ 1110a243), phase2 run 4 + local
# frontier analysis: docs/DECISIONS.md D23. These are pre-registration values.
THETA_SURPRISE = 0.45
RHO_REINFORCE = 0.70                  # reinforce_min_sim (D22)

# Promotion at 2 occurrences from 2 distinct tasks: set on Phase 0 recurrence
# evidence before registration (docs/phase0-findings.md §11.1, D25). The spec's
# §6 said 3; the kernel default (memkernel.gates.PromotionPolicy) stays 3.
CODE_PROMOTION_POLICY = PromotionPolicy(
    min_occurrences=2,
    min_distinct_inputs=2,
    eligible_labels=frozenset({"bad"}),
    cluster_similarity=0.60,          # D23
    require_separation_of_duties=True,
    schedule_every_ticks=1,           # Phase 3: one tick == one nightly run
)
