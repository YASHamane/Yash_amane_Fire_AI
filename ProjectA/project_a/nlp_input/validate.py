"""nlp_input/validate.py

WHAT:  Rule-based validator for fields extracted from plain-language input.
WHY:   LLMs frequently hallucinate or overlook subtle domain constraints.
       A hard rule-based validator ensures no invalid, contradictory, or out-of-range
       numbers pass downstream into the tax calculation engine.
HOW:   Inspects the extracted dictionary and raises MissingFieldError, AmbiguousInputError,
       or ContradictionError if business rules are violated.
"""
from __future__ import annotations

from core.errors import AmbiguousInputError, ContradictionError, MissingFieldError


def validate_extracted_data(data: dict) -> None:
    """Validates extracted fields, raising domain errors on failure."""
    # 1. Gross salary required
    gross = data.get("gross_salary")
    if gross is None:
        raise MissingFieldError(["gross_salary"])
    if not isinstance(gross, int) or gross < 0:
        raise AmbiguousInputError("gross_salary", "Gross salary must be a positive integer.")

    # 2. Age band required
    age_band = data.get("age_band")
    if not age_band:
        raise MissingFieldError(["age_band"])
    if age_band not in ("below_60", "60_to_79", "80_plus"):
        raise AmbiguousInputError("age_band", f"Unknown age band '{age_band}'.")

    # 3. Contradictions: Basic salary cannot exceed gross salary
    basic = data.get("basic_salary", 0)
    if basic > gross:
        raise ContradictionError(
            ["basic_salary", "gross_salary"],
            f"Basic salary ({basic}) cannot exceed gross salary ({gross})."
        )

    # 4. Contradictions: HRA with explicit zero rent / conflicting rent statements
    rent = data.get("rent_paid_annual", 0)
    hra = data.get("hra_received", 0)
    claims_hra = data.get("claims_hra", False) or hra > 0
    pays_no_rent = data.get("pays_no_rent", False)
    has_conflicting_rent = data.get("conflicting_rent_statements", False)

    if has_conflicting_rent or (pays_no_rent and (claims_hra or rent > 0)):
        raise ContradictionError(
            ["rent_paid_annual", "hra_received"],
            "User stated they pay no rent or live with parents, but claimed HRA or rent deductions."
        )

    # 5. Conditional HRA checks: If claiming HRA, both rent and basic salary must be provided
    if claims_hra:
        if rent == 0:
            raise MissingFieldError(["rent_paid_annual"])
        if basic == 0:
            raise MissingFieldError(["basic_salary"])

    # 6. Check negative values
    for field in ("section_80c", "section_80ccd_1b", "section_80d_self_family",
                  "section_80d_parents", "home_loan_interest"):
        val = data.get(field, 0)
        if isinstance(val, int) and val < 0:
            raise AmbiguousInputError(field, "Deduction amount cannot be negative.")
