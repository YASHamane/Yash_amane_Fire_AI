"""tests/test_parser.py

WHAT:  Tests plain-language extraction, rule-based validation, and clarifying question generation.
WHY:   The pipeline must "ask, don't guess". It must never guess missing required fields
       or let contradictions produce bad tax numbers.
"""
import json
from pathlib import Path

import pytest

from core.schema import TaxpayerInput
from nlp_input.extract import parse_and_validate

USER_DESCRIPTIONS = json.loads(
    (Path(__file__).parent / "user_descriptions.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("item", USER_DESCRIPTIONS, ids=[d["id"] for d in USER_DESCRIPTIONS])
def test_user_descriptions_behavior(item):
    inp, question = parse_and_validate(item["text"])
    expected_status = item["expected_status"]

    if expected_status == "valid":
        assert inp is not None, f"Expected valid TaxpayerInput for {item['id']}, got question: {question}"
        assert question is None
        for k, v in item.get("expected_field_values", {}).items():
            assert getattr(inp, k) == v, f"Mismatch in field {k} for {item['id']}: expected {v}, got {getattr(inp, k)}"
    else:
        assert inp is None, f"Expected clarification/error for {item['id']}, but got TaxpayerInput"
        assert question is not None, f"Expected clarifying question for {item['id']}"
        assert len(question) > 10
