"""project_a/ui/api_handlers.py

WHAT:  Backend API handlers serving JSON endpoints for the interactive UI.
WHY:   Decouples business logic from HTTP transport so each handler is a testable pure function.
HOW:   Accepts dictionaries parsed from HTTP requests, invokes tax engines or loads benchmarks,
       and returns structured JSON-ready dictionaries.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from core.schema import AgeBand, CityType, TaxpayerInput
from impl_a_rules.engine import calculate as calc_rules
from impl_c_llm_compiled.runtime import calculate as calc_compiled
from nlp_input.extract import parse_and_validate

PROJECT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_DIR / "results"
CASES_DIR = PROJECT_DIR / "tests" / "cases"


def build_taxpayer_input(raw: dict[str, Any]) -> TaxpayerInput:
    """Safely constructs a TaxpayerInput from a UI request dictionary."""
    age_band: AgeBand = raw.get("age_band", "below_60")  # type: ignore
    city_type: CityType = raw.get("city_type", "non_metro")  # type: ignore
    return TaxpayerInput(
        gross_salary=int(raw.get("gross_salary", 0)),
        age_band=age_band,
        basic_salary=int(raw.get("basic_salary", 0)),
        hra_received=int(raw.get("hra_received", 0)),
        rent_paid_annual=int(raw.get("rent_paid_annual", 0)),
        city_type=city_type,
        section_80c=int(raw.get("section_80c", 0)),
        section_80ccd_1b=int(raw.get("section_80ccd_1b", 0)),
        section_80d_self_family=int(raw.get("section_80d_self_family", 0)),
        section_80d_parents=int(raw.get("section_80d_parents", 0)),
        parents_are_senior=bool(raw.get("parents_are_senior", False)),
        home_loan_interest=int(raw.get("home_loan_interest", 0)),
    )


def handle_calculate(payload: dict[str, Any]) -> dict[str, Any]:
    """Calculates tax across the requested engine(s) for a given taxpayer."""
    fy = str(payload.get("fy", "2024-25"))
    engine = str(payload.get("engine", "all"))
    inp = build_taxpayer_input(payload.get("taxpayer", {}))

    res_a = calc_rules(inp, fy=fy)
    res_c = calc_compiled(inp, fy=fy)

    out: dict[str, Any] = {
        "fy": fy,
        "input": asdict(inp),
        "impl_a": asdict(res_a),
        "impl_c": asdict(res_c),
    }

    if engine in ("impl_b", "all"):
        try:
            from impl_b_llm_runtime.engine import calculate as calc_llm
            res_b = calc_llm(inp, fy=fy, use_cache=True)
            out["impl_b"] = asdict(res_b)
        except Exception as err:
            out["impl_b_error"] = str(err)

    return out


def handle_parse(payload: dict[str, Any]) -> dict[str, Any]:
    """Parses plain natural language salary description into structured input or question."""
    text = str(payload.get("text", "")).strip()
    if not text:
        return {"valid": False, "question": "Please provide your salary and tax details."}
    inp, question = parse_and_validate(text)
    if inp is not None:
        return {"valid": True, "data": asdict(inp), "question": None}
    return {"valid": False, "data": None, "question": question}


def _read_json_file(filename: str) -> dict[str, Any]:
    """Helper to safely read a benchmark JSON file."""
    path = RESULTS_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def handle_benchmarks() -> dict[str, Any]:
    """Loads all precomputed benchmark results from disk."""
    return {
        "accuracy": _read_json_file("accuracy.json"),
        "latency": _read_json_file("latency.json"),
        "cost": _read_json_file("cost.json"),
        "determinism": _read_json_file("determinism.json"),
        "traceability": _read_json_file("traceability.json"),
        "parser_eval": _read_json_file("parser_eval.json"),
        "change_experiment": _read_json_file("change_experiment.json"),
    }


def handle_official_checks() -> list[dict[str, Any]]:
    """Returns official ITD portal test records and oracle parity status."""
    path = CASES_DIR / "official_calc_check.csv"
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records.append({
                "case_id": row["case_id"],
                "description": row["description"],
                "oracle_old": int(row["oracle_old"]),
                "oracle_new": int(row["oracle_new"]),
                "official_old": int(row["official_old"]),
                "official_new": int(row["official_new"]),
                "match": (row["oracle_old"] == row["official_old"] and
                          row["oracle_new"] == row["official_new"]),
                "screenshot_ref": row["screenshot_ref"],
            })
    return records


def handle_law_diff() -> dict[str, Any]:
    """Returns comparative statutory parameters between FY 2024-25 and FY 2025-26."""
    return {
        "parameters": [
            {
                "feature": "Standard Deduction (Sec 115BAC)",
                "fy2024_25": "₹50,000",
                "fy2025_26": "₹75,000",
                "delta": "+₹25,000 deduction",
                "citation": "Finance Act 2025, Sec 16(ia) read with Sec 115BAC(1A)",
            },
            {
                "feature": "Sec 87A Rebate Income Threshold",
                "fy2024_25": "₹7,00,000",
                "fy2025_26": "₹12,00,000",
                "delta": "+₹5,00,000 threshold",
                "citation": "Finance Act 2025, Amendment to Sec 87A proviso",
            },
            {
                "feature": "Sec 87A Maximum Rebate Amount",
                "fy2024_25": "₹25,000",
                "fy2025_26": "₹60,000",
                "delta": "+₹35,000 max rebate",
                "citation": "Finance Act 2025, Amendment to Sec 87A proviso",
            },
            {
                "feature": "Zero-Tax Salary Ceiling (New Regime)",
                "fy2024_25": "₹7,50,000",
                "fy2025_26": "₹12,75,000",
                "delta": "₹5.25L more income tax-free",
                "citation": "₹12L rebate limit + ₹75k standard deduction",
            },
            {
                "feature": "New Regime Tax Slabs",
                "fy2024_25": "0-3L (0%), 3-7L (5%), 7-10L (10%), 10-12L (15%), 12-15L (20%), >15L (30%)",
                "fy2025_26": "0-4L (0%), 4-8L (5%), 8-12L (10%), 12-16L (15%), 16-20L (20%), 20-24L (25%), >24L (30%)",
                "delta": "Expanded slabs up to ₹24L with lower progression",
                "citation": "Finance Act 2025, First Schedule & Sec 115BAC",
            },
        ]
    }
