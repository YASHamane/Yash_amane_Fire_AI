"""impl_a_rules/surcharge.py

WHAT:  Surcharge on tax for high incomes, with marginal relief at each threshold.
WHY:   Marginal relief stops tax from rising by more than the income above a threshold.
HOW:   Uses the previous tier's rate for "tax at the threshold", because income exactly
       at a threshold does not exceed it (interpretation noted in rule_text section 9).
"""
from __future__ import annotations

from fractions import Fraction

from core.money import pct
from impl_a_rules.slabs import tax_on_slabs


def surcharge(tax_after_rebate: Fraction, total_income: int, cfg: dict,
              slabs: list[dict]) -> tuple[Fraction, Fraction]:
    """Return (surcharge after relief, relief given)."""
    tiers = cfg["tiers"]
    hit = [t for t in tiers if total_income > t["above"]]
    if not hit:
        return Fraction(0), Fraction(0)
    idx = len(hit) - 1
    prev_rate = tiers[idx - 1]["rate_pct"] if idx > 0 else 0
    amount = pct(tax_after_rebate, hit[idx]["rate_pct"])
    relief = Fraction(0)
    if cfg.get("marginal_relief", False):
        threshold = hit[idx]["above"]
        cap = pct(tax_on_slabs(threshold, slabs), 100 + prev_rate) + (total_income - threshold)
        if tax_after_rebate + amount > cap:
            relief = tax_after_rebate + amount - cap
            amount -= relief
    return amount, relief
