"""memkernel — the domain-independent kernel for EXP-001 v2.0.

Everything in this package is kernel: it knows nothing about code, defects,
GitHub, or models. Domain behaviour enters only through the three seams in
`memkernel.seams` (outcome oracle, similarity, promotion policy).
"""
from .buffer import EpisodicBuffer
from .gates import PromotionGate, PromotionPolicy, SurpriseGate
from .kernel import Kernel, KernelConfig
from .ledger import Ledger
from .records import Label, MemoryObject, Record
from .store import MemoryStore
from .vclock import VectorClock

__all__ = [
    "EpisodicBuffer",
    "Kernel",
    "KernelConfig",
    "Label",
    "Ledger",
    "MemoryObject",
    "MemoryStore",
    "PromotionGate",
    "PromotionPolicy",
    "Record",
    "SurpriseGate",
    "VectorClock",
]
