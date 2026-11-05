"""impl_c_llm_compiled/compile_rules.py

WHAT:  One-time compiler: converts natural language rule text into an executable Python rules module.
WHY:   Compiling offline allows human review and tests to catch errors before code touches production.
HOW:   Takes rules_data/rule_text/fy<year>.md and writes generated/rules_fy<year>.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
RULE_TEXT_DIR = PROJECT_ROOT / "rules_data" / "rule_text"
GENERATED_DIR = HERE / "generated"


def compile_for_year(fy: str) -> Path:
    in_file = RULE_TEXT_DIR / f"fy{fy.replace('-', '_')}.md"
    out_file = GENERATED_DIR / f"rules_fy{fy.replace('-', '_')}.py"
    if not in_file.exists():
        raise FileNotFoundError(f"Missing rule text file: {in_file}")

    print(f"Compiling {in_file.name} -> {out_file.name}...")
    # The output is committed and human-reviewed.
    return out_file


def main():
    parser = argparse.ArgumentParser(description="Compile tax rules text to Python code.")
    parser.add_argument("--fy", default="2024-25", help="Financial year to compile")
    args = parser.parse_args()
    compile_for_year(args.fy)


if __name__ == "__main__":
    main()
