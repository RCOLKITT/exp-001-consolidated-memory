import itertools

import pytest

from memkernel import Kernel, KernelConfig, PromotionPolicy
from memkernel.seams import PassthroughOracle, TokenJaccardSimilarity


def fixed_clock(start: float = 1_700_000_000.0, step: float = 1.0):
    c = itertools.count()
    return lambda: start + next(c) * step


@pytest.fixture
def make_kernel():
    def _make(**overrides):
        policy = overrides.pop("policy", PromotionPolicy())
        cfg = KernelConfig(policy=policy, **overrides)
        return Kernel(cfg, TokenJaccardSimilarity(), PassthroughOracle(), clock=fixed_clock())

    return _make
