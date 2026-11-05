"""make.py: Cross-platform command runner matching the Makefile targets."""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def run_cmd(args: list[str], cwd: Path = ROOT) -> None:
    print(f">> Running: {' '.join(args)}")
    res = subprocess.run(args, cwd=str(cwd))
    if res.returncode != 0:
        sys.exit(res.returncode)


def target_setup():
    run_cmd([PY, "-m", "pip", "install", "-r", "requirements.txt"])


def target_test():
    run_cmd([PY, "tests/cases/generate_cases.py"])
    run_cmd([PY, "-m", "pytest", "tests", "-q"])


def target_bench():
    run_cmd([PY, "bench/run_accuracy.py"])
    run_cmd([PY, "bench/run_determinism.py"])
    run_cmd([PY, "bench/run_latency.py"])
    run_cmd([PY, "bench/run_cost.py"])
    run_cmd([PY, "bench/run_traceability.py"])


def target_parse_eval():
    run_cmd([PY, "bench/run_parser_eval.py"])


def target_change():
    run_cmd([PY, "bench/run_change_experiment.py"])


def target_report():
    run_cmd([PY, "bench/make_report.py"])


def target_clean():
    for f in glob.glob(str(ROOT / "results" / "*.json")):
        try:
            os.remove(f)
        except OSError:
            pass
    for d in [ROOT / ".pytest_cache", ROOT / "__pycache__"]:
        shutil.rmtree(d, ignore_errors=True)
    print("Cleaned results and cache files.")


def target_ui():
    run_cmd([PY, "-m", "ui.server"])


def target_all():
    target_setup()
    target_test()
    target_bench()
    target_parse_eval()
    target_change()
    target_report()


TARGETS = {
    "all": target_all,
    "setup": target_setup,
    "test": target_test,
    "bench": target_bench,
    "parse-eval": target_parse_eval,
    "change": target_change,
    "report": target_report,
    "clean": target_clean,
    "ui": target_ui,
}


def main():
    target_name = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target_name not in TARGETS:
        print(f"Unknown target: {target_name}. Available: {', '.join(TARGETS)}")
        sys.exit(1)
    TARGETS[target_name]()


if __name__ == "__main__":
    main()
