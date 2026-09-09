"""Power calculation for Gate 2 / §9.4 (two-proportion, per-arm n).

    python -m phase2.power --p0 0.55 --mde 0.15 [--alpha 0.05 --power 0.8]
    python -m phase2.power --p0 0.55 --n 120        # MDE achievable at n per arm

The arms are paired (same tasks), so this normal-approximation, independent-
groups formula is conservative; use it for the floor, not for the analysis.
"""
from __future__ import annotations

import argparse
import math
import sys
from statistics import NormalDist


def n_per_arm(p0: float, mde: float, alpha: float = 0.05, power: float = 0.8) -> int:
    p1 = p0 + mde
    if not (0 < p0 < 1 and 0 < p1 < 1):
        raise ValueError("p0 and p0+mde must be in (0,1)")
    z_a = NormalDist().inv_cdf(1 - alpha / 2)
    z_b = NormalDist().inv_cdf(power)
    pbar = (p0 + p1) / 2
    num = (z_a * math.sqrt(2 * pbar * (1 - pbar)) + z_b * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2
    return math.ceil(num / mde**2)


def mde_at(p0: float, n: int, alpha: float = 0.05, power: float = 0.8, tol: float = 1e-4) -> float:
    """Smallest lift detectable with n per arm (bisection on n_per_arm)."""
    lo, hi = tol, 1 - p0 - tol
    if n_per_arm(p0, hi, alpha, power) > n:
        return float("nan")
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if n_per_arm(p0, mid, alpha, power) <= n:
            hi = mid
        else:
            lo = mid
    return round(hi, 4)


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--p0", type=float, required=True, help="control-arm localization rate (Phase 0)")
    ap.add_argument("--mde", type=float, help="minimum detectable effect, absolute (0.15 = 15 pts)")
    ap.add_argument("--n", type=int, help="eval tasks per arm available")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--power", type=float, default=0.8)
    a = ap.parse_args(argv)
    if a.mde:
        print(f"n per arm for p0={a.p0}, MDE={a.mde}: {n_per_arm(a.p0, a.mde, a.alpha, a.power)}")
    if a.n:
        print(f"MDE at n={a.n} per arm, p0={a.p0}: {mde_at(a.p0, a.n, a.alpha, a.power)}")
    if not (a.mde or a.n):
        ap.error("give --mde or --n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
