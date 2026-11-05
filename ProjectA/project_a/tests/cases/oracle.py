"""tests/cases/oracle.py

WHAT:  An independent, deliberately plain calculator for FY 2024-25 and FY 2025-26.
       It produces the EXPECTED values stored in cases_fy*.json.

WHY:   Test expectations must not come from the code under test (circular) or
       from an LLM. This oracle is written separately from impl_a_rules, uses
       the official slab table in its cumulative form ("12,500 + 20% above 5L",
       exactly as the ITD page prints it), and keeps its constants in this file.
       If oracle and impl_a disagree, either the YAML or a formula is wrong.

HOW:   generate_cases.py calls oracle(); the answer is checked against the
       Income Tax Department's official calculator for 30+ cases (CSV).

LAW:   See rules_data/sources.md and rules_data/rule_text/*.md.
"""
from __future__ import annotations

from fractions import Fraction as F

# (lower bound, tax already due at that bound, rate % above it)
OLD_TABLE = {
    "below_60": [(0, 0, 0), (250000, 0, 5), (500000, 12500, 20), (1000000, 112500, 30)],
    "60_to_79": [(0, 0, 0), (300000, 0, 5), (500000, 10000, 20), (1000000, 110000, 30)],
    "80_plus": [(0, 0, 0), (500000, 0, 20), (1000000, 100000, 30)],
}

NEW_TABLE_2024_25 = [
    (0, 0, 0), (300000, 0, 5), (700000, 20000, 10), (1000000, 50000, 15),
    (1200000, 80000, 20), (1500000, 140000, 30)
]

NEW_TABLE_2025_26 = [
    (0, 0, 0), (400000, 0, 5), (800000, 20000, 10), (1200000, 60000, 15),
    (1600000, 120000, 20), (2000000, 200000, 25), (2400000, 300000, 30)
]

SURCHARGE_OLD = [(5000000, 10), (10000000, 15), (20000000, 25), (50000000, 37)]
SURCHARGE_NEW = [(5000000, 10), (10000000, 15), (20000000, 25)]


def _slab(income: int, table) -> F:
    lower, base, rate = [row for row in table if row[0] <= income][-1]
    return F(base) + F(income - lower) * rate / 100


def _sur_rate(income: int, tiers) -> int:
    rates = [r for above, r in tiers if income > above]
    return rates[-1] if rates else 0


def _nearest10(x: F) -> int:
    whole = int(x // 1)  # ignore paise
    return ((whole + 5) // 10) * 10


def _hra(i: dict) -> F:
    if i["hra_received"] == 0 or i["rent_paid_annual"] == 0:
        return F(0)
    share = 50 if i["city_type"] == "metro" else 40
    basic = F(i["basic_salary"])
    return max(F(0), min(F(i["hra_received"]), i["rent_paid_annual"] - basic / 10, basic * share / 100))


def total_income(i: dict, regime: str, fy: str = "2024-25") -> int:
    g = i["gross_salary"]
    if regime == "new":
        std = 75000  # Rs 75,000 for both 2024-25 and 2025-26 under new regime
        return _nearest10(max(F(0), F(g) - min(std, g)))
    hra = _hra(i)
    std = max(F(0), min(F(50000), g - hra))
    gti = max(F(0), g - hra - std - min(i["home_loan_interest"], 200000))
    senior = i["age_band"] != "below_60"
    via = (min(i["section_80c"], 150000) + min(i["section_80ccd_1b"], 50000)
           + min(i["section_80d_self_family"], 50000 if senior else 25000)
           + min(i["section_80d_parents"], 50000 if i["parents_are_senior"] else 25000))
    return _nearest10(max(F(0), gti - via))


def oracle(i: dict, regime: str, fy: str = "2024-25") -> dict:
    """Return {'total_income': int, 'tax': int} for one regime."""
    ti = total_income(i, regime, fy)
    table = OLD_TABLE[i["age_band"]] if regime == "old" else (
        NEW_TABLE_2025_26 if fy == "2025-26" else NEW_TABLE_2024_25
    )
    tiers = SURCHARGE_OLD if regime == "old" else SURCHARGE_NEW
    tax = _slab(ti, table)

    if regime == "old" and ti <= 500000:
        tax -= min(tax, 12500)
    elif regime == "new":
        rebate_limit = 1200000 if fy == "2025-26" else 700000
        max_rebate = 60000 if fy == "2025-26" else 25000
        if ti <= rebate_limit:
            tax -= min(tax, max_rebate)
        elif tax > (ti - rebate_limit):
            tax = F(ti - rebate_limit)

    def with_surcharge(x: int) -> F:
        return _slab(x, table) * (100 + _sur_rate(x, tiers)) / 100

    before_cess = tax
    if _sur_rate(ti, tiers):
        th = max(above for above, _ in tiers if ti > above)
        before_cess = min(with_surcharge(ti), with_surcharge(th) + (ti - th))
    return {"total_income": ti, "tax": _nearest10(before_cess * 104 / 100)}
