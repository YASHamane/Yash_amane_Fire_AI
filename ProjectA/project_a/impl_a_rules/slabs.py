"""impl_a_rules/slabs.py

WHAT:  Progressive slab tax: apply each rate only to the part of income inside its band.
WHY:   Slab maths is the base of both regimes; keeping it in one tiny pure function makes
       it easy to test and easy to explain.
HOW:   engine.py picks the slab list for the regime and age band from the rules data.
"""
from __future__ import annotations

from fractions import Fraction

from core.money import pct


def tax_on_slabs(income: int, slabs: list[dict]) -> Fraction:
    """Exact tax (may hold paise) on `income`. Each slab: {upto, rate_pct}; upto None = no limit."""
    tax = Fraction(0)
    lower = 0
    for band in slabs:
        upto = band["upto"]
        top = income if upto is None else min(income, upto)
        if top > lower:
            tax += pct(top - lower, band["rate_pct"])
        if upto is None or income <= upto:
            break
        lower = upto
    return tax
