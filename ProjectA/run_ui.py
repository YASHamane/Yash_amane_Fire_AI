"""One-command runner to launch the Project A Income-Tax Engine Interactive UI.

Usage:
    python run_ui.py [--port 8500] [--no-browser]
"""
import sys
from pathlib import Path

# Add project_a directory to sys.path
BASE_DIR = Path(__file__).resolve().parent / "project_a"
sys.path.insert(0, str(BASE_DIR))

from ui.server import main

if __name__ == "__main__":
    main()
