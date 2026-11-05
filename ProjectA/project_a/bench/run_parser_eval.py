"""bench/run_parser_eval.py

WHAT:  Evaluates Task 3 plain-language parser across the 50 user descriptions.
WHY:   Quantifies extraction field accuracy, clarification precision/recall, and guessing rate.
HOW:   Compares parser decisions against expected statuses in user_descriptions.json.
       Writes results/parser_eval.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nlp_input.extract import parse_and_validate

DESCRIPTIONS_FILE = ROOT / "tests" / "user_descriptions.json"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def evaluate_parser() -> dict:
    cases = json.loads(DESCRIPTIONS_FILE.read_text(encoding="utf-8"))
    total_cases = len(cases)

    true_positives_clarify = 0   # needed clarification and asked
    false_positives_clarify = 0  # was valid but asked
    false_negatives_clarify = 0  # needed clarification but guessed / proceeded
    true_negatives_clarify = 0   # was valid and proceeded correctly

    field_checks = 0
    field_matches = 0

    for c in cases:
        text = c["text"]
        expected_status = c["expected_status"]
        inp, question = parse_and_validate(text)

        needs_clarification = (expected_status != "valid")
        asked_clarification = (inp is None and question is not None)

        if needs_clarification and asked_clarification:
            true_positives_clarify += 1
        elif not needs_clarification and asked_clarification:
            false_positives_clarify += 1
        elif needs_clarification and not asked_clarification:
            false_negatives_clarify += 1
        else:
            true_negatives_clarify += 1

        if expected_status == "valid" and inp is not None:
            expected_fields = c.get("expected_field_values", {})
            for k, expected_val in expected_fields.items():
                field_checks += 1
                if getattr(inp, k) == expected_val:
                    field_matches += 1

    field_accuracy = round(field_matches / field_checks * 100.0, 2) if field_checks else 100.0
    precision_clarify = round(true_positives_clarify / (true_positives_clarify + false_positives_clarify) * 100.0, 2) if (true_positives_clarify + false_positives_clarify) else 100.0
    recall_clarify = round(true_positives_clarify / (true_positives_clarify + false_negatives_clarify) * 100.0, 2) if (true_positives_clarify + false_negatives_clarify) else 100.0
    f1_clarify = round(2 * precision_clarify * recall_clarify / (precision_clarify + recall_clarify), 2) if (precision_clarify + recall_clarify) else 100.0
    wrongly_guessed_pct = round(false_negatives_clarify / total_cases * 100.0, 2)

    return {
        "total_descriptions_tested": total_cases,
        "field_accuracy_pct": field_accuracy,
        "clarification_precision_pct": precision_clarify,
        "clarification_recall_pct": recall_clarify,
        "clarification_f1": f1_clarify,
        "wrongly_guessed_pct": wrongly_guessed_pct,
        "confusion_matrix": {
            "true_positives_clarify": true_positives_clarify,
            "false_positives_clarify": false_positives_clarify,
            "false_negatives_clarify": false_negatives_clarify,
            "true_negatives_clarify": true_negatives_clarify
        }
    }


def main():
    print("Evaluating plain-language input parser over 50 descriptions...")
    metrics = evaluate_parser()
    out_file = RESULTS_DIR / "parser_eval.json"
    out_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Parser evaluation results written to {out_file}")
    print(f"Field Accuracy: {metrics['field_accuracy_pct']}% | Clarification Recall: {metrics['clarification_recall_pct']}% | Wrongly Guessed: {metrics['wrongly_guessed_pct']}%")


if __name__ == "__main__":
    main()
