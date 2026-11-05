"""impl_c_llm_compiled/runtime.py

WHAT:  Implementation (c): runtime engine executing compiled rules.
WHY:   Zero network calls, zero LLM latency at runtime, 100% auditable deterministic trace.
HOW:   Loads the precompiled pure Python rule module for the given FY, executes
       the progressive tax pipeline, and produces a complete TaxResult.
"""
from __future__ import annotations

import importlib
from fractions import Fraction

from core.errors import UnsupportedYearError
from core.money import floor_rupees, pct, round_income, round_payable
from core.schema import RegimeResult, TaxResult, TaxpayerInput, TraceLine


def _tax_on_slabs(income: int, slabs: list[dict]) -> Fraction:
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


def compute_regime(inp: TaxpayerInput, rules_mod, regime: str) -> RegimeResult:
    trace: list[TraceLine] = []

    def add(step: str, amount, clause: str, text: str) -> None:
        trace.append(TraceLine(step, floor_rupees(amount), clause, text))

    gross = inp.gross_salary
    add("gross_salary", gross, "Sec 15 (income from salaries)", f"Gross salary {gross}.")

    # Deductions & HRA
    hra_exempt = Fraction(0)
    if regime == "old":
        hra_cfg = rules_mod.get_hra_rules()
        if inp.hra_received > 0 and inp.rent_paid_annual > 0:
            share = hra_cfg["metro_pct"] if inp.city_type == "metro" else hra_cfg["non_metro_pct"]
            rent_excess = Fraction(inp.rent_paid_annual) - pct(inp.basic_salary, hra_cfg["rent_excess_over_salary_pct"])
            city_cap = pct(inp.basic_salary, share)
            hra_exempt = max(Fraction(0), min(Fraction(inp.hra_received), rent_excess, city_cap))
            add("hra_exemption", hra_exempt, hra_cfg["clause"], f"HRA exemption allowed: {float(hra_exempt):.0f}.")

    std_val = rules_mod.get_standard_deduction(regime)
    std = min(Fraction(std_val), max(Fraction(0), gross - hra_exempt))
    std_clause = "Sec 16(ia)" if regime == "old" else "Sec 115BAC(1A)(ii)"
    add("standard_deduction", std, std_clause, f"Standard deduction {std_val} capped at salary.")
    salary_income = max(Fraction(0), gross - hra_exempt - std)

    house_interest = Fraction(0)
    via = Fraction(0)
    if regime == "old":
        d_cfg = rules_mod.get_deductions_rules()
        if inp.home_loan_interest > 0:
            hl_cfg = d_cfg["home_loan_interest_self_occupied"]
            house_interest = Fraction(min(inp.home_loan_interest, hl_cfg["cap"]))
            add("home_loan_interest", house_interest, hl_cfg["clause"], f"Home loan interest capped at {hl_cfg['cap']}.")

        gross_total = max(Fraction(0), salary_income - house_interest)

        # 80C
        if inp.section_80c > 0:
            c80 = min(inp.section_80c, d_cfg["section_80c"]["cap"])
            add("section_80c", c80, d_cfg["section_80c"]["clause"], f"80C deduction {c80}.")
            via += c80
        # 80CCD(1B)
        if inp.section_80ccd_1b > 0:
            cnps = min(inp.section_80ccd_1b, d_cfg["section_80ccd_1b"]["cap"])
            add("section_80ccd_1b", cnps, d_cfg["section_80ccd_1b"]["clause"], f"80CCD(1B) deduction {cnps}.")
            via += cnps
        # 80D self
        if inp.section_80d_self_family > 0:
            cfg = d_cfg["section_80d_self_family"]
            cap = cfg["cap_if_senior"] if inp.age_band != "below_60" else cfg["cap"]
            c80d_self = min(inp.section_80d_self_family, cap)
            add("section_80d_self_family", c80d_self, cfg["clause"], f"80D self deduction {c80d_self}.")
            via += c80d_self
        # 80D parents
        if inp.section_80d_parents > 0:
            cfg = d_cfg["section_80d_parents"]
            cap = cfg["cap_if_senior"] if inp.parents_are_senior else cfg["cap"]
            c80d_par = min(inp.section_80d_parents, cap)
            add("section_80d_parents", c80d_par, cfg["clause"], f"80D parents deduction {c80d_par}.")
            via += c80d_par

        via = min(via, gross_total)
    else:
        gross_total = salary_income

    unit = rules_mod.ROUNDING_UNIT
    total_income = round_income(gross_total - via, unit)
    add("total_income", total_income, "Sec 288A", f"Total income rounded to nearest {unit}.")

    slabs = rules_mod.get_slabs(regime, inp.age_band)
    tax = _tax_on_slabs(total_income, slabs)
    add("tax_on_slabs", tax, "Finance Act slab rates", "Computed slab tax.")

    rebate_cfg = rules_mod.get_rebate_87a_params(regime)
    rebate = Fraction(0)
    if total_income <= rebate_cfg["limit"]:
        rebate = min(tax, Fraction(rebate_cfg["max_rebate"]))
    elif rebate_cfg.get("marginal_relief", False):
        excess = total_income - rebate_cfg["limit"]
        if tax > excess:
            rebate = tax - excess
    if rebate > 0:
        add("rebate_87a", rebate, "Sec 87A", "Rebate under Section 87A applied.")
    after_rebate = tax - rebate

    # Surcharge & marginal relief
    sur_cfg = rules_mod.get_surcharge_params(regime)
    hit = [t for t in sur_cfg["tiers"] if total_income > t["above"]]
    surch = Fraction(0)
    relief = Fraction(0)
    if hit:
        idx = len(hit) - 1
        prev_rate = sur_cfg["tiers"][idx - 1]["rate_pct"] if idx > 0 else 0
        surch = pct(after_rebate, hit[idx]["rate_pct"])
        if sur_cfg["marginal_relief"]:
            threshold = hit[idx]["above"]
            cap = pct(_tax_on_slabs(threshold, slabs), 100 + prev_rate) + (total_income - threshold)
            if after_rebate + surch > cap:
                relief = after_rebate + surch - cap
                surch -= relief
        add("surcharge", surch, "First Schedule surcharge", "Surcharge on tax.")
        if relief > 0:
            add("surcharge_marginal_relief", relief, "First Schedule marginal relief", "Marginal relief applied.")

    before_cess = after_rebate + surch
    cess_rate = rules_mod.get_cess_rate()
    cess_amount = pct(before_cess, cess_rate)
    add("cess", cess_amount, "Health and Education Cess", f"{cess_rate}% cess.")

    payable = round_payable(before_cess + cess_amount, unit)
    add("total_tax_payable", payable, "Sec 288B", f"Amount payable rounded to nearest {unit}.")

    return RegimeResult(regime, total_income, floor_rupees(before_cess), floor_rupees(cess_amount),
                        payable, tuple(trace))


def calculate(inp: TaxpayerInput, fy: str = "2024-25") -> TaxResult:
    mod_name = f"impl_c_llm_compiled.generated.rules_fy{fy.replace('-', '_')}"
    try:
        rules_mod = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        raise UnsupportedYearError(f"Compiled rules not found for FY {fy}: {mod_name}")

    old_res = compute_regime(inp, rules_mod, "old")
    new_res = compute_regime(inp, rules_mod, "new")

    clause = "Sec 115BAC (new regime default)"
    if old_res.total_tax < new_res.total_tax:
        rec, saving = "old", new_res.total_tax - old_res.total_tax
        text = f"Old regime is cheaper by {saving}."
    elif new_res.total_tax < old_res.total_tax:
        rec, saving = "new", old_res.total_tax - new_res.total_tax
        text = f"New regime is cheaper by {saving}."
    else:
        rec, saving = "new", 0
        text = f"Both regimes equal ({new_res.total_tax}); default new regime selected."

    choice_trace = (TraceLine("regime_choice", saving, clause, text),)
    return TaxResult(fy, old_res, new_res, rec, saving, choice_trace)
