"""One-command runner to launch the Project B Data-Quality Engine Interactive UI.

Usage:
    python run_ui.py
"""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from project_b.src.app import run_server

if __name__ == "__main__":
    run_server(port=8501, open_browser=True)
