"""bench/run_accuracy.py

WHAT:  Measures rupee-exact accuracy across all test cases for implementations (a), (b), (c).
WHY:   Rupee-exact correctness is the primary engineering requirement. We break it down
       by tag (slab_edge, rebate_marginal, surcharge, deductions, etc.) to show WHERE each implementation succeeds or fails.
HOW:   Compares total_tax against oracle expected values. Writes results/accuracy.json.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.errors import LLMOutputError
from core.schema import TaxpayerInput
import impl_a_rules.engine as impl_a
import impl_b_llm_runtime.engine as impl_b
import impl_c_llm_compiled.runtime as impl_c

CASES_FILE = ROOT / "tests" / "cases" / "cases_fy2024_25.json"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def evaluate_implementation(impl_fn, cases: list[dict], name: str) -> dict:
    total = len(cases)
    exact_both = 0
    tag_totals = defaultdict(int)
    tag_exact = defaultdict(int)
    failures = []

    for case in cases:
        inp = TaxpayerInput(**case["input"])
        exp_old = case["expected"]["old"]["tax"]
        exp_new = case["expected"]["new"]["tax"]
        tags = case.get("tags", [])

        for t in tags:
            tag_totals[t] += 1

        try:
            res = impl_fn(inp, "2024-25")
            match_old = (res.old.total_tax == exp_old)
            match_new = (res.new.total_tax == exp_new)
            is_exact = match_old and match_new
        except (LLMOutputError, Exception) as err:
            is_exact = False
            match_old = match_new = False
            if len(failures) < 5:
                failures.append({
                    "case_id": case["id"],
                    "error": str(err),
                    "tags": tags
                })

        if is_exact:
            exact_both += 1
            for t in tags:
                tag_exact[t] += 1
        else:
            if len(failures) < 5 and not any(f["case_id"] == case["id"] for f in failures):
                failures.append({
                    "case_id": case["id"],
                    "expected_old": exp_old,
                    "expected_new": exp_new,
                    "tags": tags
                })

    tag_accuracies = {
        t: round(tag_exact[t] / tag_totals[t] * 100.0, 1)
        for t in tag_totals
    }

    return {
        "implementation": name,
        "total_cases": total,
        "exact_matches": exact_both,
        "accuracy_pct": round(exact_both / total * 100.0, 2),
        "by_tag": tag_accuracies,
        "sample_failures": failures
    }


def main():
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    print(f"Benchmarking accuracy over {len(cases)} cases...")

    print("Evaluating (a) Hand-coded rules...")
    res_a = evaluate_implementation(impl_a.calculate, cases, "impl_a_rules")

    print("Evaluating (c) LLM-compiled rules...")
    res_c = evaluate_implementation(impl_c.calculate, cases, "impl_c_llm_compiled")

    print("Evaluating (b) LLM at query time (sampled subset for rate discipline)...")
    # Evaluate sample for LLM query-time
    sampled_cases = cases[::10]  # Representative sample across tags
    # For impl_b, raw LLMs fail on complex arithmetic and surcharge marginal relief
    # We evaluate against the sampled test cases:
    res_b = evaluate_implementation(
        lambda inp, fy: impl_b.calculate(inp, fy, use_cache=True),
        sampled_cases,
        "impl_b_llm_runtime"
    )

    out = {
        "fy": "2024-25",
        "impl_a": res_a,
        "impl_b": res_b,
        "impl_c": res_c
    }

    out_file = RESULTS_DIR / "accuracy.json"
    out_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Accuracy results written to {out_file}")
    print(f"Impl A: {res_a['accuracy_pct']}% | Impl C: {res_c['accuracy_pct']}% | Impl B: {res_b['accuracy_pct']}%")


if __name__ == "__main__":
    main()
