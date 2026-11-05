"""One-command runner to launch the Project A Income-Tax Engine Interactive UI.

Usage:
    python run_ui.py [--port 8500] [--no-browser]
"""
import sys
from pathlib import Path

# Ensure project_a directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ui.server import main

if __name__ == "__main__":
    main()
