"""nlp_input/extract.py

WHAT:  Extracts structured tax parameters from free-text user descriptions.
WHY:   Taxpayers describe their earnings and investments informally (English, Hinglish,
       LPA, Cr, per month). This module translates unstructured text into normalized fields
       with confidence scores.
HOW:   Uses structured extraction patterns, handling currency units (Lakh, Crore, K, pm),
       Hinglish expressions, and bidirectional syntax ("1.5L in 80C" vs "80C of 1.5L").
"""
from __future__ import annotations

import re
from typing import Any

from core.errors import AmbiguousInputError, TaxEngineError
from core.schema import TaxpayerInput
from nlp_input.clarify import build_clarification_question
from nlp_input.validate import validate_extracted_data

METRO_CITIES = {"delhi", "mumbai", "kolkata", "chennai", "new delhi"}


def _parse_amount(val_str: str) -> int | None:
    if not val_str:
        return None
    s = val_str.lower().strip().replace(",", "")
    if any(w in s for w in ["good", "decent", "handsome", "approx", "some"]):
        return None

    # Crore
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:cr|crore|crores)\b", s)
    if m:
        return int(round(float(m.group(1)) * 10000000))

    # Lakh / LPA / L (handles "18L", "18 L", "1.5L", "15 lakh")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|lpa|(?<=\d)l\b|\bl\b)", s)
    if m:
        return int(round(float(m.group(1)) * 100000))

    # Thousand / K
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:k|thousand|thousands)\b", s)
    if m:
        return int(round(float(m.group(1)) * 1000))

    # Plain digits >= 1000
    m = re.search(r"\b(\d{4,9})\b", s)
    if m:
        return int(m.group(1))

    return None


def _find_amount_around_keywords(text: str, keywords: list[str]) -> int | None:
    """Finds amount either immediately before or after any of the keywords."""
    for kw in keywords:
        # Pattern 1: amount directly before keyword (e.g. "1.5L in 80c", "50k in nps", "25000 health insurance")
        m1 = re.search(rf"(\d+(?:\.\d+)?\s*(?:cr|crore|lakh|lakhs|lac|lpa|(?<=\d)l\b|\bl\b|k|thousand)?|\d{{4,9}})\s*(?:in|towards|for)?\s*\b{kw}\b", text)
        if m1:
            amt = _parse_amount(m1.group(1))
            if amt and amt > 0:
                return amt

        # Pattern 2: keyword followed by amount (e.g. "80c: 1.5L", "basic 6 lakh")
        m2 = re.search(rf"\b{kw}\b\s*(?:is|of|investment|contribution|paid|received|for self|interest)?\s*[:=]?\s*([0-9.,]+(?:\s*(?:cr|crore|lakh|lakhs|lac|lpa|(?<=\d)l\b|\bl\b|k|thousand))?)", text)
        if m2:
            amt = _parse_amount(m2.group(1))
            if amt and amt > 0:
                if any(p in text for p in ["per month", "/month", "pm"]) and any(p in m2.group(0) for p in ["month", "pm"]):
                    amt *= 12
                return amt
    return None


def extract_fields_rule_based(text: str) -> dict[str, Any]:
    t = text.lower()
    res: dict[str, Any] = {
        "gross_salary": None,
        "age_band": None,
        "basic_salary": 0,
        "hra_received": 0,
        "rent_paid_annual": 0,
        "city_type": "non_metro",
        "section_80c": 0,
        "section_80ccd_1b": 0,
        "section_80d_self_family": 0,
        "section_80d_parents": 0,
        "parents_are_senior": False,
        "home_loan_interest": 0,
        "pays_no_rent": False,
        "claims_hra": False,
        "conflicting_rent_statements": False,
        "confidence": {}
    }

    # Rent flags
    if any(phrase in t for phrase in [
        "no rent", "dont pay rent", "don't pay rent", "not paying rent",
        "live with parents", "living with parents", "rent nahi", "kuch rent nahi"
    ]):
        res["pays_no_rent"] = True

    if "hra" in t or "house rent allowance" in t:
        res["claims_hra"] = True

    # Check city
    for c in METRO_CITIES:
        if c in t:
            res["city_type"] = "metro"
            break

    # Age band
    age_match = re.search(r"\b(?:age|umar|aged)\s*(\d{2})\b|\b(\d{2})\s*(?:years|yrs|saal)\b", t)
    if age_match:
        age_val = int(age_match.group(1) or age_match.group(2))
        res["age_band"] = "80_plus" if age_val >= 80 else ("60_to_79" if age_val >= 60 else "below_60")
        res["confidence"]["age_band"] = 0.95
    elif any(w in t for w in ["super senior", "80+", "80 plus"]):
        res["age_band"] = "80_plus"
    elif any(w in t for w in ["senior citizen", "retired", "60+"]):
        res["age_band"] = "60_to_79"
    elif any(w in t for w in ["young", "fresher", "20s", "30s", "below 60"]):
        res["age_band"] = "below_60"

    # Parents senior
    if any(w in t for w in ["senior parent", "parents are senior", "mother is 6", "father is 6", "parents 6", "elderly parent"]):
        res["parents_are_senior"] = True

    # Vague salary expressions must not extract any number
    has_vague_salary = any(w in t for w in ["decent salary", "good package", "handsome salary", "good salary"])

    # Ambiguous raw number for salary check (e.g. "earning 15", "salary is 20")
    amb_m = re.search(r"\b(?:earning|earn|salary\s+is|salary)\s+(\d{1,2})\b(?!\s*(?:\.\d+|lakh|lpa|k|cr|crore|thousand))", t)
    if amb_m:
        res["gross_salary"] = -1

    # Gross salary extraction
    if res["gross_salary"] != -1 and not has_vague_salary:
        # Check "earn/earning [amount] per month"
        pm_m = re.search(r"(?:earn|earning|salary)\s+([0-9.,]+(?:\s*(?:lakh|lacs|lac|l|k|thousand))?)\s*(?:per month|/month|pm)", t)
        if pm_m:
            amt = _parse_amount(pm_m.group(1))
            if amt:
                res["gross_salary"] = amt * 12
                res["confidence"]["gross_salary"] = 0.95

        # Check explicitly tied to salary/package/ctc/earning (e.g. "annual package 18L", "salary 1.2 crore", "45L package")
        if not res["gross_salary"]:
            sal_m1 = re.search(r"\b(?:salary|package|ctc|earning|gross|income)\s*(?:is|of|hai)?\s*[:=]?\s*([0-9.,]+(?:\s*(?:lakh|lakhs|lac|lacs|lpa|(?<=\d)l\b|\bl\b|cr|crore|k|thousand))?)", t)
            if sal_m1:
                amt = _parse_amount(sal_m1.group(1))
                if amt:
                    res["gross_salary"] = amt
                    res["confidence"]["gross_salary"] = 0.95

        # Check "[amount] package/ctc/salary"
        if not res["gross_salary"]:
            sal_m2 = re.search(r"([0-9.,]+\s*(?:lakh|lakhs|lac|lacs|lpa|(?<=\d)l\b|\bl\b|cr|crore))\s*(?:ctc|package|salary)\b", t)
            if sal_m2:
                amt = _parse_amount(sal_m2.group(1))
                if amt and amt >= 100000:
                    res["gross_salary"] = amt
                    res["confidence"]["gross_salary"] = 0.90

        # Check "earning [amount]" or "earn [amount]"
        if not res["gross_salary"]:
            sal_m3 = re.search(r"\b(?:earning|earn|kamata hoon|income)\s+([0-9.,]+(?:\s*(?:lakh|lakhs|lac|lacs|lpa|(?<=\d)l\b|\bl\b|cr|crore)))\b", t)
            if sal_m3:
                amt = _parse_amount(sal_m3.group(1))
                if amt and amt >= 100000:
                    res["gross_salary"] = amt
                    res["confidence"]["gross_salary"] = 0.90

    # Rent paid
    rent_amt = _find_amount_around_keywords(t, ["rent", "rent paid"])
    if rent_amt:
        if any(p in t for p in ["per month", "/month", "pm"]) and "rent" in t and ("month" in t or rent_amt < 60000):
            m_pm = re.search(r"(\d+(?:\.\d+)?\s*(?:k|thousand)?|\d{4,6})\s*(?:rent\s+per\s+month|rent\s+/month|rent\s+pm|per\s+month\s+rent)", t)
            if m_pm:
                rent_amt = _parse_amount(m_pm.group(1)) * 12
        res["rent_paid_annual"] = rent_amt
        if res["pays_no_rent"] and rent_amt > 0:
            res["conflicting_rent_statements"] = True

    # Basic salary
    basic_amt = _find_amount_around_keywords(t, ["basic", "basic salary"])
    if basic_amt:
        res["basic_salary"] = basic_amt

    # HRA received
    hra_amt = _find_amount_around_keywords(t, ["hra", "hra received", "hra component"])
    if hra_amt:
        res["hra_received"] = hra_amt
        res["claims_hra"] = True

    # 80C
    c_amt = _find_amount_around_keywords(t, ["80c", "ppf", "elss", "lic", "pf"])
    if c_amt:
        res["section_80c"] = c_amt

    # 80CCD(1B)
    nps_amt = _find_amount_around_keywords(t, ["nps", "80ccd", "80ccd(1b)"])
    if nps_amt:
        res["section_80ccd_1b"] = nps_amt

    # 80D
    med_amt = _find_amount_around_keywords(t, ["health insurance", "mediclaim", "medical insurance", "80d"])
    if med_amt:
        res["section_80d_self_family"] = med_amt

    # Home loan
    hl_amt = _find_amount_around_keywords(t, ["home loan", "housing loan", "loan interest"])
    if hl_amt:
        res["home_loan_interest"] = hl_amt

    return res


def parse_and_validate(text: str) -> tuple[TaxpayerInput | None, str | None]:
    data = extract_fields_rule_based(text)
    if data.get("gross_salary") == -1:
        err = AmbiguousInputError("gross_salary", "Salary number has no unit (e.g. Lakhs, Thousands).")
        return None, build_clarification_question(err)

    try:
        validate_extracted_data(data)
    except TaxEngineError as err:
        return None, build_clarification_question(err)

    inp = TaxpayerInput(
        gross_salary=data["gross_salary"],
        age_band=data["age_band"],
        basic_salary=data.get("basic_salary", 0),
        hra_received=data.get("hra_received", 0),
        rent_paid_annual=data.get("rent_paid_annual", 0),
        city_type=data.get("city_type", "non_metro"),
        section_80c=data.get("section_80c", 0),
        section_80ccd_1b=data.get("section_80ccd_1b", 0),
        section_80d_self_family=data.get("section_80d_self_family", 0),
        section_80d_parents=data.get("section_80d_parents", 0),
        parents_are_senior=data.get("parents_are_senior", False),
        home_loan_interest=data.get("home_loan_interest", 0)
    )
    return inp, None
