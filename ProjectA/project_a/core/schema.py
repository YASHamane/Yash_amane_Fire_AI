"""core/schema.py

WHAT:  The shared data contracts for Project A: the taxpayer's input, one
       line of explanation (TraceLine), the per-regime result, and the final
       answer that compares both regimes.

WHY:   All three implementations (hand-coded rules, LLM at query time,
       LLM-compiled rules) and the plain-language parser must speak the SAME
       language. If they share these types, we can compare them rupee by rupee
       and run one test-suite against all of them.

HOW:   nlp_input/ produces a TaxpayerInput. Each impl_*/engine.py exposes
       calculate(inp: TaxpayerInput, fy: str) -> TaxResult. The bench/ scripts
       compare TaxResult objects.

RULES: Money is ALWAYS an integer number of rupees. Never use float for money,
       because floats cause off-by-one-rupee errors and we are graded on
       rupee-exact accuracy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Regime = Literal["old", "new"]
AgeBand = Literal["below_60", "60_to_79", "80_plus"]
CityType = Literal["metro", "non_metro"]


@dataclass(frozen=True)
class TaxpayerInput:
    """Everything we need to know about a salaried person (annual, in rupees).

    Fields with a default are "safe defaults": 0 means "this person has no such
    item". Fields WITHOUT a default are REQUIRED; the parser must ask the user
    if they are missing instead of guessing (see nlp_input/required_fields.md).
    """

    # --- Required -----------------------------------------------------
    gross_salary: int                      # total annual salary received
    age_band: AgeBand                      # decides old-regime slabs, 80D limits

    # --- Needed only if the person claims HRA ----------------------------
    basic_salary: int = 0                  # basic + DA (as per HRA rule)
    hra_received: int = 0                  # HRA component of salary
    rent_paid_annual: int = 0              # total rent paid in the year
    city_type: CityType = "non_metro"      # metro vs non-metro changes HRA %

    # --- Old-regime deductions (new regime ignores most of these) --------
    section_80c: int = 0                   # PF, ELSS, LIC, PPF, etc. (as invested)
    section_80ccd_1b: int = 0              # extra NPS contribution
    section_80d_self_family: int = 0       # health insurance: self, spouse, kids
    section_80d_parents: int = 0           # health insurance: parents
    parents_are_senior: bool = False       # parents aged 60+ -> higher 80D limit
    home_loan_interest: int = 0            # self-occupied house, Sec 24(b)

    def __post_init__(self) -> None:
        # Fail loudly on bad data; a negative amount is always a bug upstream.
        for name, value in asdict(self).items():
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise ValueError(f"{name} must not be negative, got {value}")


@dataclass(frozen=True)
class TraceLine:
    """One step of the calculation: what happened, how much, and WHY.

    `clause` is the legal reference (e.g. "Sec 87A"). The traceability
    benchmark checks that every rupee in the answer is explained by a line
    that has a non-empty clause.
    """

    step: str            # short machine-friendly name, e.g. "standard_deduction"
    amount: int          # rupees for this step (can be a deduction or a tax)
    clause: str          # legal reference, must not be empty
    explanation: str     # one human-readable sentence


@dataclass(frozen=True)
class RegimeResult:
    """Tax outcome under ONE regime, with its ordered trace."""

    regime: Regime
    taxable_income: int
    tax_before_cess: int       # after rebate and surcharge, before 4% cess
    cess: int
    total_tax: int             # final payable; THIS is what tests compare
    trace: tuple[TraceLine, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TaxResult:
    """The final answer: both regimes, the recommendation, and why."""

    fy: str                    # e.g. "2024-25"
    old: RegimeResult
    new: RegimeResult
    recommended: Regime
    savings: int               # rupees saved by choosing `recommended`
    trace: tuple[TraceLine, ...] = field(default_factory=tuple)  # regime-choice reasoning
