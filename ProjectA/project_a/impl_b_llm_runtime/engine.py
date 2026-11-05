"""impl_b_llm_runtime/engine.py

WHAT:  Implementation (b): LLM at query time. Reads rule text per request and computes tax.
WHY:   Tests whether an LLM can perform multi-step arithmetic, slab logic, and marginal
       relief faithfully from statute text alone at runtime.
HOW:   Formats rule text + input JSON into prompt, calls Gemini (temperature=0), parses JSON,
       validates against schema without post-correcting numbers, and returns TaxResult.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from core.errors import LLMOutputError, UnsupportedYearError
from core.schema import RegimeResult, TaxResult, TaxpayerInput, TraceLine
from impl_b_llm_runtime.llm_client import LLMClient

RULE_TEXT_DIR = Path(__file__).resolve().parent.parent / "rules_data" / "rule_text"
PROMPT_TEMPLATE = Path(__file__).resolve().parent / "prompt_templates" / "calculate_tax_v1.txt"


def _clean_json(raw: str) -> str:
    cleaned = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    return cleaned


def _parse_regime(data: dict, regime_name: str) -> RegimeResult:
    try:
        r = data[regime_name]
        trace_lines = [
            TraceLine(step=item["step"], amount=int(item["amount"]),
                      clause=item["clause"], explanation=item["explanation"])
            for item in r.get("trace", [])
        ]
        return RegimeResult(
            regime=r["regime"],
            taxable_income=int(r["taxable_income"]),
            tax_before_cess=int(r["tax_before_cess"]),
            cess=int(r["cess"]),
            total_tax=int(r["total_tax"]),
            trace=tuple(trace_lines)
        )
    except (KeyError, ValueError, TypeError) as err:
        raise LLMOutputError(f"Schema validation failed for {regime_name} regime: {err}")


class LLMRuntimeEngine:
    def __init__(self, client: LLMClient | None = None):
        self.client = client or LLMClient()
        self.template = PROMPT_TEMPLATE.read_text(encoding="utf-8")

    def calculate(self, inp: TaxpayerInput, fy: str = "2024-25", use_cache: bool = True) -> TaxResult:
        rule_file = RULE_TEXT_DIR / f"fy{fy.replace('-', '_')}.md"
        if not rule_file.exists():
            raise UnsupportedYearError(f"No rule text available for FY {fy}")
        rule_text = rule_file.read_text(encoding="utf-8")

        prompt = self.template.format(
            fy=fy,
            rule_text=rule_text,
            taxpayer_input_json=json.dumps(asdict(inp), indent=2)
        )

        response = self.client.generate(prompt=prompt, temperature=0.0, use_cache=use_cache)
        cleaned = _clean_json(response.text)

        # Fallback simulation if offline/empty text
        if not cleaned or cleaned == "{}":
            # If no response text, raise LLMOutputError so failure is loud, not silent
            raise LLMOutputError("Empty response from LLM runtime engine")

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as err:
            raise LLMOutputError(f"Failed to parse LLM response as JSON: {err}\nRaw text: {response.text}")

        old_res = _parse_regime(data, "old")
        new_res = _parse_regime(data, "new")
        choice_trace = tuple(
            TraceLine(step=item["step"], amount=int(item["amount"]),
                      clause=item["clause"], explanation=item["explanation"])
            for item in data.get("trace", [])
        )
        return TaxResult(
            fy=fy,
            old=old_res,
            new=new_res,
            recommended=data.get("recommended", "new"),
            savings=int(data.get("savings", 0)),
            trace=choice_trace
        )


_default_engine = LLMRuntimeEngine()


def calculate(inp: TaxpayerInput, fy: str = "2024-25", use_cache: bool = True) -> TaxResult:
    return _default_engine.calculate(inp, fy, use_cache=use_cache)
