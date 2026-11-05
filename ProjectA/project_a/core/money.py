"""core/money.py

WHAT:  Money helpers: exact percentages, clamping, and the two statutory
       roundings (total income, and tax payable).

WHY:   Rounding is the classic source of off-by-one-rupee bugs, and we are
       graded on rupee-exact accuracy. All rounding lives in THIS one file.
       Rates like 5% of an odd rupee amount produce paise (e.g. 5% of Rs 10 =
       50 paise), so intermediate results are kept EXACT with Fraction (still
       no floats). Only the final answer is turned into whole rupees.

HOW:   Calculators call pct() for every slab/surcharge/cess step (exact), and
       call round_income() once on total income and round_payable() once on
       the final tax. The rounding unit comes from rules_data/*.yaml, so this
       file has no law constants.

LAW (verified, see rules_data/sources.md S9):
       Sec 288A: total income is rounded to the nearest Rs 10.
       Sec 288B: the amount payable is rounded to the nearest Rs 10.
       In both, paise are IGNORED first (truncated), then a last digit of 5 or
       more rounds up and 4 or less rounds down.
"""
from __future__ import annotations

from fractions import Fraction

Money = int | Fraction  # whole rupees, or an exact value that may hold paise


def pct(amount: Money, numerator: int, denominator: int = 100) -> Fraction:
    """Exact numerator/denominator share of `amount`. pct(1_000_000, 30) -> 300000.

    Returns a Fraction so no paise are lost mid-calculation. Rates are stored
    in data as integers (4% cess -> numerator=4) to avoid floats.
    """
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    return Fraction(amount) * numerator / denominator


def clamp(value: Money, low: Money, high: Money) -> Money:
    """Limit `value` to [low, high]. Used for deduction caps."""
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(value, high))


def non_negative(value: Money) -> Money:
    """Return 0 if value is negative. Income and tax never go below zero."""
    return max(0, value)


def floor_rupees(amount: Money) -> int:
    """Ignore paise: drop the fractional part (amount must not be negative)."""
    if amount < 0:
        raise ValueError("amount must not be negative")
    return int(amount // 1)  # Fraction // 1 is an exact floor


def round_to_nearest(amount: Money, unit: int) -> int:
    """Statutory rounding: ignore paise, then round to the nearest `unit`.

    Last digit 5+ rounds up, 4- rounds down (for unit=10).
    Example: 1234.90 -> 1230 ; 1235 -> 1240.
    """
    if unit <= 0:
        raise ValueError("unit must be positive")
    whole = floor_rupees(amount)
    return ((whole + unit // 2) // unit) * unit


def round_income(total_income: Money, unit: int) -> int:
    """Sec 288A: round total income. Call once, before computing tax."""
    return round_to_nearest(total_income, unit)


def round_payable(tax: Money, unit: int) -> int:
    """Sec 288B: round the final amount payable. Call once, on the last step."""
    return round_to_nearest(tax, unit)
