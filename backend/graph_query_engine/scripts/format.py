"""
Format Orchestration Script.
"""

import subprocess
import sys
from pathlib import Path

engine_dir = Path(__file__).resolve().parent.parent


def main() -> int:
    """Runs code formatting with ruff format / black."""
    print("Formatting with ruff...")
    res = subprocess.run([sys.executable, "-m", "ruff", "format", str(engine_dir)])
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
