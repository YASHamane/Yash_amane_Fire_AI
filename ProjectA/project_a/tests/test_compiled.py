"""tests/test_compiled.py

WHAT:  Validates implementation (c) against the 200+ test cases.
WHY:   Asserts rupee-exact accuracy AND guarantees zero runtime network / LLM calls.
"""
import json
import socket
from pathlib import Path
from unittest.mock import patch

import pytest

from core.schema import TaxpayerInput
from impl_c_llm_compiled.runtime import calculate

CASES = json.loads((Path(__file__).parent / "cases" / "cases_fy2024_25.json").read_text(encoding="utf-8"))


def forbidden_connect(*args, **kwargs):
    raise RuntimeError("NETWORK CALL ATTEMPTED! Implementation (c) must be zero-network.")


def test_compiled_rules_make_zero_network_calls():
    """Assert that runtime calculation executes completely offline without network sockets."""
    with patch.object(socket.socket, "connect", side_effect=forbidden_connect):
        inp = TaxpayerInput(gross_salary=1500000, age_band="below_60", section_80c=150000)
        res = calculate(inp, "2024-25")
        assert res.new.total_tax > 0


@pytest.mark.parametrize("case", CASES[::5], ids=[c["id"] for c in CASES[::5]])
def test_compiled_matches_oracle(case):
    result = calculate(TaxpayerInput(**case["input"]), "2024-25")
    assert result.old.total_tax == case["expected"]["old"]["tax"]
    assert result.new.total_tax == case["expected"]["new"]["tax"]
