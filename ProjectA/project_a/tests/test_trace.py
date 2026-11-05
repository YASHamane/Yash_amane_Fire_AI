"""tests/test_trace.py

WHAT:  Checks that every rupee in the answer is explained by a trace line with a clause.
WHY:   Task 4 asks "does every rupee trace back to a specific clause?". This is the
       automatic version of that check, reused by bench/run_traceability.py.
"""
import json
from pathlib import Path

import pytest

from core.schema import TaxpayerInput
from impl_a_rules.engine import calculate

CASES = json.loads((Path(__file__).parent / "cases" / "cases_fy2024_25.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES[::7], ids=[c["id"] for c in CASES[::7]])
def test_every_line_has_a_clause_and_final_matches(case):
    result = calculate(TaxpayerInput(**case["input"]), "2024-25")
    for regime in (result.old, result.new):
        assert regime.trace, "empty trace"
        assert all(line.clause.strip() for line in regime.trace)
        assert all(line.explanation.strip() for line in regime.trace)
        assert regime.trace[-1].step == "total_tax_payable"
        assert regime.trace[-1].amount == regime.total_tax
    assert all(line.clause.strip() for line in result.trace)
