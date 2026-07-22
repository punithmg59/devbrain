# DevBrain Repository Analyzer V2 - Test Infrastructure

This directory contains the unit and integration test suite for the Repository Analyzer V2 system.

## Folder Structure

```
repository_analyzer_v2/
├── pytest.ini            # Pytest configuration file
├── .coveragerc           # Code coverage settings
├── .github/
│   └── workflows/
│       └── test.yml      # CI workflow configuration for GitHub Actions
└── tests/
    ├── README.md         # Test documentation (this file)
    ├── conftest.py       # Shared pytest fixtures (dummy repos, mock plugins, singletons)
    ├── test_config.py    # Configuration system tests (Phase 0.2)
    ├── test_models.py    # Data models tests (Phase 0.3)
    ├── test_plugin_sdk.py# Plugin SDK tests (Phase 0.4)
    ├── test_plugin_manager.py # Plugin Manager tests (Phase 0.5)
    ├── test_pipeline.py  # Pipeline orchestrator tests (Phase 0.6)
    ├── test_context.py   # PipelineContext tests (Phase 0.7)
    ├── test_logger.py    # Structured logging tests (Phase 0.8)
    ├── test_exceptions.py# Exception hierarchy tests (Phase 0.9)
    ├── test_event_bus.py# Internal EventBus tests (Phase 0.10)
    ├── test_metrics.py  # MetricsCollector tests (Phase 0.11)
    ├── test_database.py # DatabaseManager tests (Phase 0.12)
    └── test_testing_infrastructure.py # Testing infrastructure sample tests (Phase 0.13)
```

## Shared Fixtures (`conftest.py`)

- **`dummy_repo_dir`**: Generates a temporary directory with sample source files (`src/main.py`, `src/utils.py`, `src/app.ts`, `README.md`).
- **`dummy_repository_model`**: Provides a `Repository` model instance pointing to `dummy_repo_dir`.
- **`mock_python_plugin`**: Instantiates a configurable `MockLanguagePlugin` supporting `.py` files.
- **`mock_ts_plugin`**: Instantiates a configurable `MockLanguagePlugin` supporting `.ts` and `.tsx` files.
- **`reset_singletons`**: Autouse fixture ensuring `PluginManager`, `EventBus`, and `MetricsCollector` start with clean state before every test.

## Running Tests

Run the full test suite using `pytest`:

```bash
# Run all tests
python -m pytest

# Run tests with verbose output
python -m pytest -v

# Run a specific test file
python -m pytest tests/test_pipeline.py
```

## Code Coverage

Run tests with code coverage analysis:

```bash
python -m pytest --cov=. --cov-report=term-missing
```

## Continuous Integration (CI)

CI is configured via GitHub Actions in `.github/workflows/test.yml`. It automatically executes tests against Python 3.10, 3.11, and 3.12 on every push and pull request to `main` and `dev`.
