"""
Test Orchestration Script.
"""

import subprocess
import sys
from pathlib import Path

engine_dir = Path(__file__).resolve().parent.parent
backend_dir = engine_dir.parent


def main() -> int:
    """Runs pytest test suite."""
    print("Executing pytest suite...")
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/graph_query_engine/tests", "-v"],
        cwd=str(backend_dir.parent),
    )
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
