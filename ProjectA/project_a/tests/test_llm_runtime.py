"""tests/test_llm_runtime.py

WHAT:  Validates implementation (b): LLM at query time.
WHY:   Ensures prompt formatting, JSON parsing, schema validation, and loud error raising.
"""
from unittest.mock import MagicMock

import pytest

from core.errors import LLMOutputError
from core.schema import TaxpayerInput
from impl_b_llm_runtime.engine import LLMRuntimeEngine, calculate
from impl_b_llm_runtime.llm_client import LLMResponse


def test_schema_validation_failure_is_loud():
    mock_client = MagicMock()
    mock_client.generate.return_value = LLMResponse(
        text='{"invalid": "json response missing required fields"}',
        prompt_tokens=100, candidate_tokens=20, total_tokens=120, latency_ms=10.0, cached=False
    )
    engine = LLMRuntimeEngine(client=mock_client)
    inp = TaxpayerInput(gross_salary=1000000, age_band="below_60")
    with pytest.raises(LLMOutputError):
        engine.calculate(inp, "2024-25", use_cache=False)


def test_valid_json_response_parsing():
    valid_text = """{
      "fy": "2024-25",
      "old": {
        "regime": "old", "taxable_income": 950000, "tax_before_cess": 102500, "cess": 4100, "total_tax": 106600,
        "trace": [{"step": "gross_salary", "amount": 1000000, "clause": "Sec 15", "explanation": "Gross"}]
      },
      "new": {
        "regime": "new", "taxable_income": 925000, "tax_before_cess": 42500, "cess": 1700, "total_tax": 44200,
        "trace": [{"step": "gross_salary", "amount": 1000000, "clause": "Sec 15", "explanation": "Gross"}]
      },
      "recommended": "new",
      "savings": 62400,
      "trace": [{"step": "regime_choice", "amount": 62400, "clause": "Sec 115BAC", "explanation": "New is cheaper"}]
    }"""
    mock_client = MagicMock()
    mock_client.generate.return_value = LLMResponse(
        text=valid_text, prompt_tokens=200, candidate_tokens=80, total_tokens=280, latency_ms=15.0, cached=False
    )
    engine = LLMRuntimeEngine(client=mock_client)
    inp = TaxpayerInput(gross_salary=1000000, age_band="below_60")
    result = engine.calculate(inp, "2024-25", use_cache=False)
    assert result.recommended == "new"
    assert result.new.total_tax == 44200
    assert result.old.total_tax == 106600
    assert result.savings == 62400
