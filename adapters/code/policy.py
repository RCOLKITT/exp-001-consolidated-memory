"""Promotion policy constants for the code adapter (spec §6). Hand-set; no
adaptive thresholds (spec §1). Changing these after pre-registration
invalidates the result (spec §7)."""
from memkernel import PromotionPolicy

THETA_SURPRISE = 0.35

CODE_PROMOTION_POLICY = PromotionPolicy(
    min_occurrences=3,
    min_distinct_inputs=3,
    eligible_labels=frozenset({"bad"}),
    cluster_similarity=0.65,          # to be set during pre-registration
    require_separation_of_duties=True,
    schedule_every_ticks=1,           # Phase 3: one tick == one nightly run
)
