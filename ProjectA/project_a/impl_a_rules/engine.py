"""impl_a_rules/engine.py

WHAT:  Implementation (a): the hand-coded calculator. Rules in YAML, logic in Python.
WHY:   It is the reference design: deterministic, auditable (every step has a clause),
       and cheap. Implementations (b) and (c) are measured against it.
HOW:   calculate(inp, fy) -> TaxResult. Steps follow rule_text/*.md section 1.
"""
from __future__ import annotations

from fractions import Fraction
from functools import lru_cache

from core.money import floor_rupees, round_income, round_payable
from core.rules_loader import load_rules
from core.schema import RegimeResult, TaxResult, TaxpayerInput, TraceLine
from impl_a_rules.cess import cess
from impl_a_rules.deductions import capped_claims, home_loan_claim
from impl_a_rules.hra import hra_exemption
from impl_a_rules.rebate_87a import rebate_87a
from impl_a_rules.regime_choice import choose_regime
from impl_a_rules.slabs import tax_on_slabs
from impl_a_rules.surcharge import surcharge


@lru_cache(maxsize=8)
def _rules(fy: str) -> dict:
    return load_rules(fy)


def compute_regime(inp: TaxpayerInput, rules: dict, regime: str) -> RegimeResult:
    reg = rules["old_regime" if regime == "old" else "new_regime"]
    unit, rnd = rules["rounding"]["unit"], rules["rounding"]
    trace: list[TraceLine] = []

    def add(step: str, amount, clause: str, text: str) -> None:
        trace.append(TraceLine(step, floor_rupees(amount), clause, text))

    gross = inp.gross_salary
    add("gross_salary", gross, "Sec 15 (income from salaries)", f"Gross salary {gross}.")
    deductions = reg.get("deductions", {})
    hra_exempt = Fraction(0)
    if "hra" in deductions:
        hra_exempt, text = hra_exemption(inp, deductions["hra"])
        add("hra_exemption", hra_exempt, deductions["hra"]["clause"], text)

    sd = rules["standard_deduction"]
    std = min(Fraction(sd[regime]), max(Fraction(0), gross - hra_exempt))
    add("standard_deduction", std, sd["clause"], f"Standard deduction {sd[regime]} or salary if lower.")
    salary_income = max(Fraction(0), gross - hra_exempt - std)

    loan = home_loan_claim(inp, deductions)
    house = Fraction(loan.amount) if loan else Fraction(0)
    if loan:
        add(loan.step, loan.amount, loan.clause, loan.explanation)
    gross_total = max(Fraction(0), salary_income - house)

    claims = capped_claims(inp, deductions)
    for c in claims:
        add(c.step, c.amount, c.clause, c.explanation)
    via = min(Fraction(sum(c.amount for c in claims)), gross_total)
    if sum(c.amount for c in claims) > gross_total:
        add("chapter_via_limit", via, "Chapter VI-A aggregate limit",
            "Deductions cannot exceed gross total income.")
    total_income = round_income(gross_total - via, unit)
    add("total_income", total_income, rnd["clause"], f"Total income rounded to nearest {unit}.")

    slabs = reg["slabs"][inp.age_band if regime == "old" else "all_ages"]
    tax = tax_on_slabs(total_income, slabs)
    add("tax_on_slabs", tax, reg["slabs"]["clause"], "Tax from the slab table.")
    rebate = rebate_87a(tax, total_income, reg["rebate_87a"])
    if rebate > 0:
        add("rebate_87a", rebate, reg["rebate_87a"]["clause"], "Rebate under Section 87A.")
    after_rebate = tax - rebate

    extra, relief = surcharge(after_rebate, total_income, reg["surcharge"], slabs)
    if extra > 0:
        add("surcharge", extra, reg["surcharge"]["clause"], "Surcharge on tax.")
    if relief > 0:
        add("surcharge_marginal_relief", relief, reg["surcharge"]["clause"], "Marginal relief reduced the surcharge.")

    before_cess = after_rebate + extra
    cess_amount = cess(before_cess, rules["cess"])
    add("cess", cess_amount, rules["cess"]["clause"], f"{rules['cess']['rate_pct']}% cess on tax plus surcharge.")
    payable = round_payable(before_cess + cess_amount, unit)
    add("total_tax_payable", payable, rnd["clause"], f"Final amount rounded to nearest {unit}.")
    return RegimeResult(regime, total_income, floor_rupees(before_cess), floor_rupees(cess_amount),
                        payable, tuple(trace))


def calculate(inp: TaxpayerInput, fy: str = "2024-25") -> TaxResult:
    """Calculates tax for both regimes and returns the recommendation and traces."""
    rules = _rules(fy)
    old = compute_regime(inp, rules, "old")
    new = compute_regime(inp, rules, "new")
    rec, saving, trace = choose_regime(old, new)
    return TaxResult(fy, old, new, rec, saving, trace)
