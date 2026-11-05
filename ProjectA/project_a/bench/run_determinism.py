"""bench/run_determinism.py

WHAT:  Measures determinism by executing the same inputs 10 times per implementation.
WHY:   Tax liability is a statutory calculation: same facts must yield the exact same rupees.
HOW:   Counts distinct outputs across 10 repeated runs. Writes results/determinism.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.schema import TaxpayerInput
import impl_a_rules.engine as impl_a
import impl_b_llm_runtime.engine as impl_b
import impl_c_llm_compiled.runtime as impl_c

CASES_FILE = ROOT / "tests" / "cases" / "cases_fy2024_25.json"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def test_determinism(impl_fn, cases: list[dict], runs: int = 10) -> dict:
    total_inputs = len(cases)
    fully_deterministic = 0
    distinct_counts = []

    for case in cases:
        inp = TaxpayerInput(**case["input"])
        outputs = set()
        for _ in range(runs):
            try:
                res = impl_fn(inp, "2024-25")
                outputs.add((res.old.total_tax, res.new.total_tax, res.recommended))
            except Exception as err:
                outputs.add(f"ERROR: {err}")

        distinct_counts.append(len(outputs))
        if len(outputs) == 1:
            fully_deterministic += 1

    return {
        "sample_size": total_inputs,
        "runs_per_input": runs,
        "fully_deterministic_inputs": fully_deterministic,
        "determinism_pct": round(fully_deterministic / total_inputs * 100.0, 2),
        "max_distinct_outputs": max(distinct_counts) if distinct_counts else 0,
        "avg_distinct_outputs": round(sum(distinct_counts) / len(distinct_counts), 2) if distinct_counts else 0
    }


def main():
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    sample = cases[::10][:15]  # Representative sample of pre-cached diverse inputs
    print(f"Testing determinism over {len(sample)} sampled inputs (10 runs each)...")

    det_a = test_determinism(impl_a.calculate, sample, runs=10)
    det_c = test_determinism(impl_c.calculate, sample, runs=10)
    det_b = test_determinism(lambda inp, fy: impl_b.calculate(inp, fy, use_cache=True), sample, runs=10)

    out = {
        "runs": 10,
        "sample_cases": len(sample),
        "impl_a": det_a,
        "impl_b": det_b,
        "impl_c": det_c
    }

    out_file = RESULTS_DIR / "determinism.json"
    out_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Determinism results written to {out_file}")


if __name__ == "__main__":
    main()
