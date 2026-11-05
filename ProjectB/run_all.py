"""Master Pipeline Execution Script for Project B.

Reproduces every number, benchmark, and report in RESULTS_B.md from scratch:
1. Ingests raw NYC 311 2023 dataset and official USPS reference data
2. Profiles raw data to discover real production defects
3. Derives 100% verified clean reference set
4. Injects 12 controlled corruption types across multiple rates (Task 2)
5. Executes all 3 detector families (Rules, Stats, LLM) (Task 3)
6. Benchmarks detection rates, false alarms, cost, and throughput (Task 4)
7. Executes Production Hybrid Pipeline and baselines (Task 5)
8. Renders RESULTS_B.md and DECISION_MATRIX.md (Task 6 & Deliverables)
"""

import sys
import time
from pathlib import Path

# Add project_b to path
sys.path.append(str(Path(__file__).resolve().parent))

from project_b.src.download import (
    download_official_zip_borough_reference,
    find_candidate_csv,
    process_provided_csv,
)
from project_b.src.profile import (
    load_raw_dataset,
    profile_raw_data,
    build_clean_dataset,
)
from project_b.src.injector import generate_evaluation_dataset
from project_b.src.metrics import run_full_benchmark
from project_b.src.hybrid import run_hybrid_comparison
from project_b.src.report import (
    generate_results_markdown,
    generate_decision_matrix_markdown,
)
from project_b.src.config import RESULTS_DIR


def main():
    print("=" * 78)
    print("  PROJECT B: DATA-QUALITY CHECKS (RULES vs STATS vs LLM REVIEW)")
    print("=" * 78)
    t_start = time.time()

    # Step 1: Ingestion
    print("\n[Step 1/6] Ingesting NYC 311 Data & Reference Boundaries...")
    download_official_zip_borough_reference()
    candidate = find_candidate_csv()
    if candidate:
        process_provided_csv(candidate)
    else:
        print("Using existing consolidated parquet...")

    # Step 2: Profiling Real Data
    print("\n[Step 2/6] Profiling Raw 2023 Data for Real Defects...")
    raw_df = load_raw_dataset()
    summary, examples = profile_raw_data(raw_df)
    summary.to_csv(RESULTS_DIR / "profile_summary.csv", index=False)
    with open(RESULTS_DIR / "profile_examples.json", "w", encoding="utf-8") as f:
        import json
        json.dump(examples, f, indent=2, default=str)
    clean_df = build_clean_dataset(raw_df)

    # Step 3: Injecting Controlled Corruptions
    print("\n[Step 3/6] Generating Fixed Evaluation Suite (12 Problem Types)...")
    generate_evaluation_dataset(clean_df)

    # Step 4: Benchmarking All Detector Families
    print("\n[Step 4/6] Benchmarking Rules, Stats, and LLM Review across Batches...")
    run_full_benchmark()

    # Step 5: Hybrid Pipeline Execution
    print("\n[Step 5/6] Executing Hybrid Pipeline & Architecture Comparison...")
    run_hybrid_comparison()

    # Step 6: Rendering Reports
    print("\n[Step 6/6] Generating Deliverable Markdown Reports...")
    generate_results_markdown()
    generate_decision_matrix_markdown()

    total_elapsed = time.time() - t_start
    print("\n" + "=" * 78)
    print(f"  SUCCESS: All numbers reproduced from scratch in {total_elapsed:.2f} seconds!")
    print("  Deliverables:")
    print("    - RESULTS_B.md")
    print("    - DECISION_MATRIX.md")
    print("    - AI_USAGE.md")
    print("    - EXPLAINED.md")
    print("    - project_b/results/*.csv & *.json")
    print("=" * 78)


if __name__ == "__main__":
    main()
