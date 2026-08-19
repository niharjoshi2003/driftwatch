from __future__ import annotations

import math


def ewma(previous: float | None, current: float, alpha: float) -> float:
    if previous is None:
        return current
    return alpha * current + (1 - alpha) * previous


def two_proportion_z(p_base: float, n_base: float, p_cur: float, n_cur: float) -> float:
    if n_base <= 0 or n_cur <= 0:
        return 0.0
    x_base = p_base * n_base
    x_cur = p_cur * n_cur
    p_pool = (x_base + x_cur) / (n_base + n_cur)
    denom = p_pool * (1 - p_pool) * (1 / n_base + 1 / n_cur)
    if denom <= 0:
        return 0.0
    return (p_base - p_cur) / math.sqrt(denom)
