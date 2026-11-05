"""Measurement and Benchmarking Harness for Project B.

Task 4: Evaluates all 3 detector families across all 12 problem types and 3 injection rates:
- Detection Rate (Recall)
- Precision
- False-Alarm Rate on verified clean batches
- Cost per million rows ($)
- Throughput (rows/second on this laptop)
- Explainability score (0-3 rubric)

Saves all metrics to results/benchmark_metrics.csv and results/clean_false_alarms.csv.
"""

import sys
import json
import time
import platform
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np

# Add project_b to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from project_b.src.config import (
    INJECTED_DATA_DIR,
    CLEAN_DATA_DIR,
    RESULTS_DIR,
    PROBLEM_TYPES,
    EVAL_INJECTION_RATES,
    GEMINI_PRICE_INPUT_PER_M,
    GEMINI_PRICE_OUTPUT_PER_M,
    CPU_COST_PER_HOUR,
)
from project_b.src.detectors.rules import detect_with_rules
from project_b.src.detectors.stats import detect_with_stats
from project_b.src.detectors.llm import detect_with_llm


def measure_clean_false_alarms() -> pd.DataFrame:
    """Measures false-alarm rate across clean batches for every detector family and problem type."""
    clean_batch_files = sorted(list(INJECTED_DATA_DIR.glob("clean_batch_*.parquet")))
    if not clean_batch_files:
        raise FileNotFoundError("Clean batches not found in data/injected/. Run injector.py first.")

    records = []
    detector_dispatchers = {
        "rule": detect_with_rules,
        "statistical": detect_with_stats,
        "llm": detect_with_llm,
    }

    for p_type in PROBLEM_TYPES:
        for family, fn in detector_dispatchers.items():
            false_alarms = 0
            total_clean_batches = len(clean_batch_files)
            
            for bf in clean_batch_files:
                df_clean = pd.read_parquet(bf)
                res = fn(p_type, df_clean)
                if res["is_corrupted"]:
                    false_alarms += 1

            far = false_alarms / total_clean_batches
            records.append({
                "problem_type": p_type,
                "detector_family": family,
                "clean_batches_tested": total_clean_batches,
                "clean_batches_flagged": false_alarms,
                "false_alarm_rate": round(far, 4),
            })

    df_far = pd.DataFrame(records)
    out_path = RESULTS_DIR / "clean_false_alarms.csv"
    df_far.to_csv(out_path, index=False)
    print(f"Saved clean false-alarm results to {out_path}")
    return df_far


def compute_cost_per_million(family: str, runtime_sec: float, n_rows: int, in_tokens: int = 0, out_tokens: int = 0) -> float:
    """Calculates normalized cost per 1M rows.
    
    Rules/Stats: Hardware CPU amortized cost ($0.0425/CPU-hr on cloud instance).
    LLM: Gemini 1.5 Flash paid-tier token prices ($0.075/1M input, $0.30/1M output).
    """
    scale_factor = 1_000_000 / max(1, n_rows)
    
    if family == "llm":
        total_token_cost = (in_tokens / 1_000_000 * GEMINI_PRICE_INPUT_PER_M) + \
                           (out_tokens / 1_000_000 * GEMINI_PRICE_OUTPUT_PER_M)
        return round(total_token_cost * scale_factor, 4)
    else:
        # CPU compute time converted to hours
        cpu_hours = runtime_sec / 3600.0
        return round(cpu_hours * CPU_COST_PER_HOUR * scale_factor, 6)


def run_full_benchmark() -> pd.DataFrame:
    """Runs end-to-end benchmark across all 12 problem types, 3 rates, and 3 detector families."""
    clean_far_df = measure_clean_false_alarms()
    far_map = dict(zip(
        zip(clean_far_df["problem_type"], clean_far_df["detector_family"]),
        clean_far_df["false_alarm_rate"]
    ))

    detector_dispatchers = {
        "rule": detect_with_rules,
        "statistical": detect_with_stats,
        "llm": detect_with_llm,
    }

    benchmark_rows = []

    for p_type in PROBLEM_TYPES:
        for rate in EVAL_INJECTION_RATES:
            rate_pct = int(round(rate * 100))
            batch_file = INJECTED_DATA_DIR / f"injected_{p_type}_rate_{rate_pct}pct.parquet"
            gt_file = INJECTED_DATA_DIR / f"gt_{p_type}_rate_{rate_pct}pct.json"
            
            if not batch_file.exists() or not gt_file.exists():
                continue

            df = pd.read_parquet(batch_file)
            with open(gt_file, "r", encoding="utf-8") as f:
                gt = json.load(f)

            is_batch_level = (gt.get("level") == "batch")
            gt_indices = set(gt.get("corrupted_indices", []))
            n_rows = len(df)

            for family, fn in detector_dispatchers.items():
                t0 = time.perf_counter()
                res = fn(p_type, df)
                runtime = time.perf_counter() - t0

                flagged = set(res.get("flagged_indices", []))
                is_flagged = res.get("is_corrupted", False)

                # Precision and Recall calculation
                if is_batch_level:
                    # Batch-level problem
                    recall = 1.0 if is_flagged else 0.0
                    precision = 1.0 if is_flagged else 0.0
                else:
                    # Row-level problem
                    tp = len(gt_indices & flagged)
                    fp = len(flagged - gt_indices)
                    fn_count = len(gt_indices - flagged)
                    
                    recall = tp / max(1, len(gt_indices))
                    precision = tp / max(1, (tp + fp)) if (tp + fp) > 0 else (1.0 if is_flagged else 0.0)

                throughput = round(n_rows / max(0.0001, runtime), 1)
                in_tok = res.get("input_tokens", 0)
                out_tok = res.get("output_tokens", 0)
                cost_per_m = compute_cost_per_million(family, runtime, n_rows, in_tok, out_tok)
                far = far_map.get((p_type, family), 0.0)

                benchmark_rows.append({
                    "problem_type": p_type,
                    "detector_family": family,
                    "injection_rate": rate,
                    "recall": round(recall, 4),
                    "precision": round(precision, 4),
                    "false_alarm_rate": far,
                    "cost_per_million": cost_per_m,
                    "throughput_rows_sec": throughput,
                    "explainability_score": res.get("explainability_score", 2),
                    "runtime_sec": round(runtime, 5),
                    "llm_calls": res.get("llm_calls", 0),
                })

    bench_df = pd.DataFrame(benchmark_rows)
    out_file = RESULTS_DIR / "benchmark_metrics.csv"
    bench_df.to_csv(out_file, index=False)
    print(f"Saved complete benchmark results ({len(bench_df)} runs) to {out_file}")
    return bench_df


if __name__ == "__main__":
    run_full_benchmark()
