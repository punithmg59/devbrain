"""
Unit test for Architecture Validator script and static checks.
"""

from pathlib import Path
from graph_query_engine.architecture import ArchitectureValidator, RuleSeverity


def test_architecture_validator_clean_pass():
    """
    Verifies that the static Architecture Validator completes with ZERO errors.
    """
    engine_dir = Path(__file__).resolve().parent.parent.parent
    validator = ArchitectureValidator(engine_dir)
    violations = validator.validate_all()

    errors = [v for v in violations if v.severity == RuleSeverity.ERROR]
    assert len(errors) == 0, f"Architecture violations detected: {errors}"
