"""impl_a_rules/hra.py

WHAT:  House Rent Allowance exemption: the least of three amounts (old regime only).
WHY:   HRA is the most error-prone old-regime rule (three limbs, metro vs non-metro),
       so it gets its own small module and its own explanation string for the trace.
HOW:   engine.py calls this only when the regime's rules contain an `hra` block.
"""
from __future__ import annotations

from fractions import Fraction

from core.money import pct
from core.schema import TaxpayerInput


def hra_exemption(inp: TaxpayerInput, cfg: dict) -> tuple[Fraction, str]:
    """Return (exempt amount, explanation). No HRA received or no rent paid -> exemption 0."""
    if inp.hra_received == 0 or inp.rent_paid_annual == 0:
        return Fraction(0), "No HRA received or no rent paid, so no HRA exemption."
    share = cfg["metro_pct"] if inp.city_type == "metro" else cfg["non_metro_pct"]
    received = Fraction(inp.hra_received)
    rent_excess = Fraction(inp.rent_paid_annual) - pct(inp.basic_salary, cfg["rent_excess_over_salary_pct"])
    city_cap = pct(inp.basic_salary, share)
    exempt = max(Fraction(0), min(received, rent_excess, city_cap))
    text = (f"Least of HRA received {float(received):.0f}, rent minus "
            f"{cfg['rent_excess_over_salary_pct']}% of salary {float(rent_excess):.0f}, "
            f"{share}% of salary {float(city_cap):.0f}.")
    return exempt, text
