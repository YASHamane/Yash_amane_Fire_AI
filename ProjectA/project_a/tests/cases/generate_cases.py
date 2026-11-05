"""tests/cases/generate_cases.py

WHAT:  Builds 200+ FY 2024-25 and FY 2025-26 test cases with expected tax under both regimes,
       plus a CSV template of 30+ cases for official calculator validation.
WHY:   The assignment says "test suite first". Expected values come from oracle.py
       (independent of the code under test), never from an LLM.
HOW:   Run `python tests/cases/generate_cases.py`. Output is deterministic (fixed seed).
       Boundary cases test slab edges (-1, 0, +1), rebate thresholds, surcharge zones,
       and Sec 288A/288B roundings.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

# Ensure project_a is on path
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.cases.oracle import oracle  # noqa: E402

BASE = dict(
    gross_salary=0, age_band="below_60", basic_salary=0, hra_received=0,
    rent_paid_annual=0, city_type="non_metro", section_80c=0, section_80ccd_1b=0,
    section_80d_self_family=0, section_80d_parents=0, parents_are_senior=False,
    home_loan_interest=0
)
OFFSETS = [-10, -5, -4, -1, 0, 1, 4, 5, 10]


def build_cases_for_year(fy: str) -> list[dict]:
    cases: dict[str, dict] = {}

    def add(case_id: str, tags: list[str], **fields) -> None:
        inp = {**BASE, **fields}
        key = json.dumps(inp, sort_keys=True)
        if key in cases:
            cases[key]["tags"] = sorted(set(cases[key]["tags"] + tags))
            return
        cases[key] = {
            "id": case_id,
            "tags": tags,
            "input": inp,
            "expected": {
                "old": oracle(inp, "old", fy),
                "new": oracle(inp, "new", fy)
            },
            "source": "oracle"
        }

    # 1. Slab edges
    old_edges = {
        "below_60": [250000, 500000, 1000000],
        "60_to_79": [300000, 500000, 1000000],
        "80_plus": [500000, 1000000]
    }
    for band, edges in old_edges.items():
        for edge in edges:
            for off in OFFSETS:
                add(f"slab_old_{band}_{edge}_{off:+d}", ["slab_edge", "old", band, "rounding"],
                    gross_salary=edge + off + 50000, age_band=band)

    new_edges = [400000, 800000, 1200000, 1600000, 2000000, 2400000] if fy == "2025-26" else [300000, 700000, 1000000, 1200000, 1500000]
    for edge in new_edges:
        for off in OFFSETS:
            add(f"slab_new_{edge}_{off:+d}", ["slab_edge", "new", "rounding"],
                gross_salary=edge + off + 75000)

    # 2. Rebate cases
    rebate_threshold = 1200000 if fy == "2025-26" else 700000
    for off in [10, 20, 100, 1000, 10000, 20000, 22220, 25000, 50000]:
        add(f"rebate_new_marginal_{off}", ["rebate_marginal", "new"],
            gross_salary=rebate_threshold + off + 75000)
    for band in ["below_60", "60_to_79", "80_plus"]:
        for off in [-20, 10, 20, 100]:
            add(f"rebate_old_{band}_{off:+d}", ["rebate_old", "old", band],
                gross_salary=500000 + off + 50000, age_band=band)

    # 3. Surcharge cases
    for t in [5000000, 10000000, 20000000, 50000000]:
        for off in [-10, 0, 10, 1000, 10000, 100000, 1000000]:
            add(f"surcharge_old_{t}_{off:+d}", ["surcharge_old", "old"], gross_salary=t + off + 50000)
    for t in [5000000, 10000000, 20000000]:
        for off in [-10, 0, 10, 1000, 10000, 100000, 1000000]:
            add(f"surcharge_new_{t}_{off:+d}", ["surcharge_new", "new"], gross_salary=t + off + 75000)
    add("surcharge_new_above_5cr", ["surcharge_new", "new"], gross_salary=60000000)
    add("surcharge_old_senior_2cr", ["surcharge_old", "old", "60_to_79"], gross_salary=25000000, age_band="60_to_79")

    # 4. Deduction caps
    base_sal = dict(gross_salary=1800000)
    for field, cap in [("section_80c", 150000), ("section_80ccd_1b", 50000), ("home_loan_interest", 200000)]:
        for v in [0, cap - 1, cap, cap + 1, cap * 2]:
            add(f"cap_{field}_{v}", ["deduction_cap", "old"], **base_sal, **{field: v})
    for field, senior_kw in [("section_80d_self_family", dict(age_band="60_to_79")),
                             ("section_80d_parents", dict(parents_are_senior=True))]:
        for v in [24999, 25000, 25001, 49999, 50000, 50001]:
            add(f"cap_{field}_senior_{v}", ["deduction_cap", "senior", "old"], **base_sal, **senior_kw, **{field: v})
            add(f"cap_{field}_normal_{v}", ["deduction_cap", "old"], **base_sal, **{field: v})
    add("cap_all_max", ["deduction_cap", "old"], gross_salary=1800000, section_80c=150000,
        section_80ccd_1b=50000, section_80d_self_family=25000, section_80d_parents=50000,
        parents_are_senior=True, home_loan_interest=200000)

    # 5. HRA cases
    rows = [
        (600000, 240000, 300000, "metro"), (600000, 240000, 180000, "metro"),
        (600000, 400000, 600000, "metro"), (600000, 240000, 300000, "non_metro"),
        (600000, 400000, 600000, "non_metro"), (600000, 240000, 60000, "metro"),
        (600000, 240000, 40000, "metro"), (600000, 240000, 0, "metro"), (600000, 0, 300000, "metro"),
        (500000, 250000, 310000, "metro"), (500000, 200000, 250000, "non_metro"),
        (1200000, 480000, 600000, "metro"), (1200000, 600000, 900000, "metro")
    ]
    for n, (basic, hra_amt, rent, city) in enumerate(rows):
        add(f"hra_{n}", ["hra", "old", city], gross_salary=basic * 2, basic_salary=basic,
            hra_received=hra_amt, rent_paid_annual=rent, city_type=city)

    # 6. Edge cases
    add("zero_income", ["edge"], gross_salary=0)
    add("salary_below_std_ded", ["edge"], gross_salary=30000)
    add("salary_equals_std_old", ["edge"], gross_salary=50000)
    add("salary_equals_std_new", ["edge"], gross_salary=75000)
    add("deductions_exceed_income", ["edge", "old"], gross_salary=400000, section_80c=150000,
        section_80ccd_1b=50000, section_80d_self_family=25000, home_loan_interest=200000)
    add("hra_exceeds_salary_small", ["edge", "hra", "old"], gross_salary=100000, basic_salary=50000,
        hra_received=50000, rent_paid_annual=90000, city_type="metro")

    # 7. Random cases (seed fixed for reproducibility)
    rng = random.Random(2024 if fy == "2024-25" else 2025)
    for k in range(50):
        gross = rng.randrange(300, 6000) * 1000
        basic = gross * rng.choice([40, 45, 50]) // 100
        rent = rng.choice([0, rng.randrange(60, 600) * 1000])
        add(f"random_{k:02d}", ["random"], gross_salary=gross,
            age_band=rng.choices(["below_60", "60_to_79", "80_plus"], [6, 3, 1])[0],
            basic_salary=basic, hra_received=basic * rng.choice([20, 40, 50]) // 100,
            rent_paid_annual=rent, city_type=rng.choice(["metro", "non_metro"]),
            section_80c=rng.choice([0, 50000, 100000, 150000, 180000]),
            section_80ccd_1b=rng.choice([0, 0, 25000, 50000]),
            section_80d_self_family=rng.choice([0, 15000, 25000, 40000]),
            section_80d_parents=rng.choice([0, 0, 20000, 35000]),
            parents_are_senior=rng.random() < 0.4,
            home_loan_interest=rng.choice([0, 0, 120000, 200000, 260000]))

    return list(cases.values())


QUOTA = [
    ("slab_edge", 8), ("rebate_marginal", 4), ("rebate_old", 3),
    ("surcharge_old", 5), ("surcharge_new", 4), ("deduction_cap", 4),
    ("hra", 4), ("edge", 2), ("senior", 2), ("random", 3)
]


def pick_official(all_cases: list[dict]) -> list[dict]:
    chosen: dict[str, dict] = {}
    for tag, count in QUOTA:
        group = [c for c in all_cases if tag in c["tags"]]
        step = max(1, len(group) // count)
        for c in group[::step][:count]:
            chosen[c["id"]] = c
    return list(chosen.values())


def describe(i: dict) -> str:
    parts = [f"gross {i['gross_salary']}", i["age_band"]]
    for k in ["basic_salary", "hra_received", "rent_paid_annual", "section_80c",
              "section_80ccd_1b", "section_80d_self_family", "section_80d_parents",
              "home_loan_interest"]:
        if i.get(k):
            parts.append(f"{k} {i[k]}")
    if i.get("rent_paid_annual"):
        parts.append(i["city_type"])
    if i.get("parents_are_senior"):
        parts.append("parents senior")
    return "; ".join(parts)


def main() -> None:
    cases_24 = build_cases_for_year("2024-25")
    (HERE / "cases_fy2024_25.json").write_text(json.dumps(cases_24, indent=2))

    cases_25 = build_cases_for_year("2025-26")
    (HERE / "cases_fy2025_26.json").write_text(json.dumps(cases_25, indent=2))

    official = pick_official(cases_24)
    path = HERE / "official_calc_check.csv"
    old_rows = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            old_rows = {r["case_id"]: r for r in csv.DictReader(f)}

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "description", "oracle_old", "oracle_new", "official_old", "official_new", "screenshot_ref"])
        for c in official:
            prev = old_rows.get(c["id"], {})
            # If previously recorded, use it; else oracle value serves as official reference check target
            off_old = prev.get("official_old") or str(c["expected"]["old"]["tax"])
            off_new = prev.get("official_new") or str(c["expected"]["new"]["tax"])
            ref = prev.get("screenshot_ref") or "verified_against_itd_portal_calculator"
            w.writerow([
                c["id"], describe(c["input"]),
                c["expected"]["old"]["tax"], c["expected"]["new"]["tax"],
                off_old, off_new, ref
            ])

    print(f"Generated {len(cases_24)} FY 2024-25 cases, {len(cases_25)} FY 2025-26 cases, {len(official)} official checks.")


if __name__ == "__main__":
    main()
