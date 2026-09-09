import pytest

from memkernel import Kernel, KernelConfig, PromotionPolicy
from memkernel.seams import PassthroughOracle, TokenJaccardSimilarity


from memkernel.kernel import counting_clock as fixed_clock  # noqa: E402


@pytest.fixture
def make_kernel():
    def _make(**overrides):
        policy = overrides.pop("policy", PromotionPolicy())
        cfg = KernelConfig(policy=policy, **overrides)
        return Kernel(cfg, TokenJaccardSimilarity(), PassthroughOracle(), clock=fixed_clock())

    return _make
