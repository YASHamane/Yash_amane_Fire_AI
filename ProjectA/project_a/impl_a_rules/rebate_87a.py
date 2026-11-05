"""impl_a_rules/rebate_87a.py

WHAT:  Section 87A rebate, including the new-regime marginal relief just above the limit.
WHY:   The rebate cliff at Rs 5L (old) and Rs 7L / 12L (new) is the most-tested boundary.
HOW:   Takes the slab tax and rounded total income; returns the rebate (exact).
"""
from __future__ import annotations

from fractions import Fraction


def rebate_87a(tax: Fraction, total_income: int, cfg: dict) -> Fraction:
    """Rebate = lesser of tax and max_rebate if income <= limit; else marginal relief if enabled."""
    limit = cfg["income_limit"]
    if total_income <= limit:
        return min(tax, Fraction(cfg["max_rebate"]))
    if cfg.get("marginal_relief", False):
        excess = total_income - limit
        if tax > excess:
            return tax - excess  # tax payable becomes exactly the excess over the limit
    return Fraction(0)
