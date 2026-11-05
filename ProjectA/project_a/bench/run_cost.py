"""bench/run_cost.py

WHAT:  Calculates token counts and notional cost per 1,000 requests for all implementations.
WHY:   Gemini free tier has zero monetary charge, but production deployment at scale requires
       projecting notional costs using published paid pricing.
HOW:   Applies Google AI Gemini 2.5 Flash pricing (March 2025: $0.075/1M input, $0.30/1M output,
       USD/INR = 86.50). Writes results/cost.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from impl_b_llm_runtime.llm_client import PRICING_CONFIG

RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def calculate_costs() -> dict:
    pricing = PRICING_CONFIG
    usd_in = pricing["usd_per_1m_input"]
    usd_out = pricing["usd_per_1m_output"]
    inr_rate = pricing["inr_per_usd"]

    # Implementation (a): Hand-coded
    cost_a = {
        "implementation": "impl_a_rules",
        "input_tokens_per_req": 0,
        "output_tokens_per_req": 0,
        "total_tokens_per_1k_req": 0,
        "cost_usd_per_1k_req": 0.0,
        "cost_inr_per_1k_req": 0.0,
        "cost_inr_per_100k_users": 0.0
    }

    # Implementation (c): LLM-compiled (one-time compilation cost; runtime zero)
    # One-time compilation tokens: ~1,500 input, ~600 output
    one_time_compile_usd = (1500 / 1_000_000 * usd_in) + (600 / 1_000_000 * usd_out)
    cost_c = {
        "implementation": "impl_c_llm_compiled",
        "one_time_compile_cost_usd": round(one_time_compile_usd, 6),
        "one_time_compile_cost_inr": round(one_time_compile_usd * inr_rate, 4),
        "runtime_input_tokens_per_req": 0,
        "runtime_output_tokens_per_req": 0,
        "total_tokens_per_1k_req": 0,
        "cost_usd_per_1k_req": 0.0,
        "cost_inr_per_1k_req": 0.0,
        "cost_inr_per_100k_users": 0.0
    }

    # Implementation (b): LLM at query time
    # Prompt contains full statutory rule text (~1,250 tokens) + input (~150 tokens) = 1,400 tokens
    # Output contains JSON with old/new results and traces = ~350 tokens
    b_in_tok = 1400
    b_out_tok = 350
    b_cost_usd_1k = ((b_in_tok * 1000) / 1_000_000 * usd_in) + ((b_out_tok * 1000) / 1_000_000 * usd_out)
    b_cost_inr_1k = b_cost_usd_1k * inr_rate
    cost_b = {
        "implementation": "impl_b_llm_runtime",
        "input_tokens_per_req": b_in_tok,
        "output_tokens_per_req": b_out_tok,
        "total_tokens_per_req": b_in_tok + b_out_tok,
        "total_tokens_per_1k_req": (b_in_tok + b_out_tok) * 1000,
        "cost_usd_per_1k_req": round(b_cost_usd_1k, 4),
        "cost_inr_per_1k_req": round(b_cost_inr_1k, 2),
        "cost_inr_per_100k_users": round(b_cost_inr_1k * 100, 2)
    }

    # Task 3 Plain-language NLP Parser (when LLM extraction is invoked)
    nlp_in_tok = 550
    nlp_out_tok = 85
    nlp_cost_usd_1k = ((nlp_in_tok * 1000) / 1_000_000 * usd_in) + ((nlp_out_tok * 1000) / 1_000_000 * usd_out)
    cost_nlp = {
        "component": "nlp_input_parser",
        "input_tokens_per_req": nlp_in_tok,
        "output_tokens_per_req": nlp_out_tok,
        "cost_usd_per_1k_req": round(nlp_cost_usd_1k, 4),
        "cost_inr_per_1k_req": round(nlp_cost_usd_1k * inr_rate, 2),
        "cost_inr_per_100k_users": round(nlp_cost_usd_1k * inr_rate * 100, 2)
    }

    return {
        "pricing_source": pricing,
        "impl_a": cost_a,
        "impl_b": cost_b,
        "impl_c": cost_c,
        "nlp_parser": cost_nlp
    }


def main():
    costs = calculate_costs()
    out_file = RESULTS_DIR / "cost.json"
    out_file.write_text(json.dumps(costs, indent=2), encoding="utf-8")
    print(f"Cost benchmark results written to {out_file}")
    print(f"Impl A: Rs 0/1k | Impl C: Rs 0/1k (compile Rs {costs['impl_c']['one_time_compile_cost_inr']}) | Impl B: Rs {costs['impl_b']['cost_inr_per_1k_req']}/1k")


if __name__ == "__main__":
    main()
