"""tests/test_rules.py

WHAT:  Runs every FY 2024-25 case against implementation (a) and compares to the oracle,
       and compares to official-calculator numbers in official_calc_check.csv.
WHY:   Rupee-exact correctness is the first grading area. Failing ids name the case,
       so a failure says which rule broke (e.g. slab_old_below_60_500000_+5).
"""
import csv
import json
from pathlib import Path

import pytest

from core.errors import UnsupportedYearError
from core.rules_loader import load_rules
from core.schema import TaxpayerInput
from impl_a_rules.engine import calculate

CASES_DIR = Path(__file__).parent / "cases"
CASES = json.loads((CASES_DIR / "cases_fy2024_25.json").read_text(encoding="utf-8"))


def test_at_least_200_cases():
    assert len(CASES) >= 200


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_matches_oracle(case):
    result = calculate(TaxpayerInput(**case["input"]), "2024-25")
    assert result.old.total_tax == case["expected"]["old"]["tax"]
    assert result.new.total_tax == case["expected"]["new"]["tax"]
    assert result.old.taxable_income == case["expected"]["old"]["total_income"]
    assert result.new.taxable_income == case["expected"]["new"]["total_income"]


def _official_rows():
    path = CASES_DIR / "official_calc_check.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("official_old", "").strip() and r.get("official_new", "").strip()]


OFFICIAL = _official_rows()


@pytest.mark.skipif(not OFFICIAL, reason="official_calc_check.csv not filled in yet")
@pytest.mark.parametrize("row", OFFICIAL, ids=[r["case_id"] for r in OFFICIAL])
def test_matches_official_calculator(row):
    case = next(c for c in CASES if c["id"] == row["case_id"])
    result = calculate(TaxpayerInput(**case["input"]), "2024-25")
    assert result.old.total_tax == int(row["official_old"])
    assert result.new.total_tax == int(row["official_new"])


def test_new_regime_disallowed_list_is_not_applied():
    """Data says these deductions are not allowed in the new regime; the engine must agree."""
    rules = load_rules("2024-25")
    assert "deductions" not in rules["new_regime"]
    assert "section_80c" in rules["new_regime"]["disallowed_in_new_regime"]


def test_unknown_year_is_a_loud_error():
    with pytest.raises(UnsupportedYearError):
        calculate(TaxpayerInput(gross_salary=1, age_band="below_60"), "1999-00")
