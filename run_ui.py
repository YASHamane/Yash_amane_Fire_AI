"""One-command runner to launch interactive UI dashboards for the Fire AI Assessment.

Usage:
    python run_ui.py               # Launches Project A Tax Engine UI (default, port 8500)
    python run_ui.py --project b   # Launches Project B Data-Quality Engine UI (port 8501)
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch Fire AI Assessment Interactive Dashboard")
    parser.add_argument("--project", choices=["a", "b"], default="a", help="Project to run (a or b, default: a)")
    parser.add_argument("--port", type=int, default=None, help="Custom port")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser")
    args, unknown = parser.parse_known_args()

    if args.project == "a":
        runner = ROOT / "ProjectA" / "run_ui.py"
        port = args.port or 8500
        cmd = [sys.executable, str(runner), "--port", str(port)]
        if args.no_browser:
            cmd.append("--no-browser")
        sys.exit(subprocess.run(cmd, cwd=str(ROOT / "ProjectA")).returncode)
    else:
        runner = ROOT / "ProjectB" / "run_ui.py"
        cmd = [sys.executable, str(runner)]
        sys.exit(subprocess.run(cmd, cwd=str(ROOT / "ProjectB")).returncode)
