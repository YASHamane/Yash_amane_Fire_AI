"""impl_a_rules/cess.py

WHAT:  4% Health and Education Cess on (tax after rebate + surcharge).
WHY:   One-line rule, kept separate so a Budget change to the rate is a data edit only.
HOW:   engine.py calls it once per regime.
"""
from __future__ import annotations

from fractions import Fraction

from core.money import pct


def cess(amount: Fraction, cfg: dict) -> Fraction:
    """Calculates Health and Education Cess as a percentage of tax + surcharge."""
    return pct(amount, cfg["rate_pct"])
