import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "ProjectA"
PY = sys.executable

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    cmd = [PY, "make.py", target]
    res = subprocess.run(cmd, cwd=str(ROOT))
    sys.exit(res.returncode)
