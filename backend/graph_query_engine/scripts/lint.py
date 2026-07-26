"""
Lint Orchestration Script.
"""

import subprocess
import sys
from pathlib import Path

engine_dir = Path(__file__).resolve().parent.parent


def main() -> int:
    """Runs ruff and mypy linters."""
    print("Running ruff check...")
    res1 = subprocess.run([sys.executable, "-m", "ruff", "check", str(engine_dir)])
    print("Running mypy check...")
    res2 = subprocess.run([sys.executable, "-m", "mypy", str(engine_dir)])
    return max(res1.returncode, res2.returncode)


if __name__ == "__main__":
    sys.exit(main())
