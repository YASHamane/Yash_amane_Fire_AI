"""tests/test_ui.py

WHAT:  Unit tests verifying the UI endpoints, data serialization, and HTML rendering.
WHY:   Ensures the interactive web dashboard works deterministically without runtime regressions.
HOW:   Invokes API handler functions and validates schema, calculations, and error handling.
"""
from ui.api_handlers import (
    handle_benchmarks,
    handle_calculate,
    handle_law_diff,
    handle_official_checks,
    handle_parse,
)
from ui.html_template import render_index_html


def test_ui_calculate_endpoint():
    payload = {
        "fy": "2024-25",
        "engine": "impl_a",
        "taxpayer": {
            "gross_salary": 1800000,
            "age_band": "below_60",
            "basic_salary": 900000,
            "section_80c": 150000,
        },
    }
    res = handle_calculate(payload)
    assert res["fy"] == "2024-25"
    assert "impl_a" in res
    assert res["impl_a"]["recommended"] in ("old", "new")
    assert res["impl_a"]["new"]["total_tax"] > 0
    assert len(res["impl_a"]["new"]["trace"]) > 0


def test_ui_parse_endpoint():
    # Valid input
    valid_res = handle_parse({"text": "I make 18 LPA in Bangalore, rent 35000 pm, age 29"})
    assert valid_res["valid"] is True
    assert valid_res["data"]["gross_salary"] == 1800000
    assert valid_res["question"] is None

    # Ambiguous input (vague salary)
    ambig_res = handle_parse({"text": "Good package with 1.5L in 80C, age 28"})
    assert ambig_res["valid"] is False
    assert ambig_res["question"] is not None
    assert len(ambig_res["question"]) > 10


def test_ui_benchmarks_and_checks():
    bench = handle_benchmarks()
    assert "accuracy" in bench
    assert "latency" in bench
    assert "cost" in bench

    checks = handle_official_checks()
    assert len(checks) >= 30
    assert all(c["match"] is True for c in checks)


def test_ui_law_diff_and_html():
    diff = handle_law_diff()
    assert len(diff["parameters"]) >= 4

    html = render_index_html()
    assert "<!DOCTYPE html>" in html
    assert "Project A" in html
    assert "Statutory Audit Trace" in html
