"""impl_a_rules/deductions.py

WHAT:  Caps the user's claimed deductions (80C, 80CCD(1B), 80D, home-loan interest).
WHY:   Caps are law, so they come from the rules data, never from the input or from code.
HOW:   engine.py passes the regime's `deductions` block; a regime with no such block
       (the new regime) gets no deductions, which is how "not allowed" is enforced.
"""
from __future__ import annotations

from typing import NamedTuple

from core.schema import TaxpayerInput

CHAPTER_VIA = ("section_80c", "section_80ccd_1b", "section_80d_self_family", "section_80d_parents")


class Claim(NamedTuple):
    step: str
    amount: int
    clause: str
    explanation: str


def _cap(name: str, cfg: dict, inp: TaxpayerInput) -> int:
    if name == "section_80d_self_family":
        senior = inp.age_band != "below_60"
    elif name == "section_80d_parents":
        senior = inp.parents_are_senior
    else:
        senior = False
    return cfg["cap_if_senior"] if senior and "cap_if_senior" in cfg else cfg["cap"]


def capped_claims(inp: TaxpayerInput, deductions: dict) -> list[Claim]:
    """Chapter VI-A claims, each limited to its cap. Zero claims are skipped."""
    claims = []
    for name in CHAPTER_VIA:
        cfg = deductions.get(name)
        claimed = getattr(inp, name)
        if cfg is None or claimed == 0:
            continue
        cap = _cap(name, cfg, inp)
        amount = min(claimed, cap)
        claims.append(Claim(name, amount, cfg["clause"], f"Claimed {claimed}, cap {cap}, allowed {amount}."))
    return claims


def home_loan_claim(inp: TaxpayerInput, deductions: dict) -> Claim | None:
    """Self-occupied home-loan interest, limited to its cap (None if regime disallows it)."""
    cfg = deductions.get("home_loan_interest_self_occupied")
    if cfg is None or inp.home_loan_interest == 0:
        return None
    amount = min(inp.home_loan_interest, cfg["cap"])
    text = f"Interest {inp.home_loan_interest}, cap {cfg['cap']}, allowed {amount}."
    return Claim("home_loan_interest", amount, cfg["clause"], text)
