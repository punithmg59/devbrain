"""
Architecture Health Check Script for Graph Query Engine.

Executes the static Architecture Validator and reports layering, import, and package boundary violations.
Exit code 0 if architecture is clean; 1 if violations exist.
"""

import sys
from pathlib import Path

# Adjust python path to import graph_query_engine if run directly
engine_dir = Path(__file__).resolve().parent.parent
backend_dir = engine_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from graph_query_engine.architecture import ArchitectureValidator, RuleSeverity


def main() -> int:
    """Executes architecture checks and returns status code."""
    print("=" * 60)
    print("RUNNING ARCHITECTURE HEALTH CHECKS...")
    print("=" * 60)

    validator = ArchitectureValidator(engine_dir)
    violations = validator.validate_all()

    errors = [v for v in violations if v.severity == RuleSeverity.ERROR]
    warnings = [v for v in violations if v.severity == RuleSeverity.WARNING]

    for violation in violations:
        prefix = "[ERROR]" if violation.severity == RuleSeverity.ERROR else "[WARN]"
        print(f"{prefix} [{violation.rule_name}] {violation.file_path}:{violation.line_number} - {violation.message}")

    print("-" * 60)
    print(f"Summary: {len(errors)} Error(s), {len(warnings)} Warning(s).")

    if errors:
        print("RESULT: ARCHITECTURE CHECK FAILED.")
        return 1

    print("RESULT: ARCHITECTURE CHECK PASSED CLEANLY!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
