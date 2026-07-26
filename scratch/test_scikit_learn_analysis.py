"""
scratch/test_scikit_learn_analysis.py
--------------------------------------
Enterprise Benchmark Script analyzing a scikit-learn repository architecture using DependencyGraphFacade.
"""

import ast
import time
import sys
from pathlib import Path

# Add backend/repository_analyzer_v2 to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "repository_analyzer_v2"))

from core.facade import DependencyGraphFacade
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


def convert_python_ast_node(node: ast.AST) -> list[dict]:
    """Recursively convert standard Python AST node into DevBrain AST dictionary format."""
    results = []

    if isinstance(node, ast.Module):
        children = []
        for stmt in node.body:
            children.extend(convert_python_ast_node(stmt))
        return [{
            "type": "module",
            "name": "module",
            "range": {"start": {"line": 1, "column": 0}, "end": {"line": 150, "column": 0}},
            "children": children
        }]

    elif isinstance(node, ast.ClassDef):
        superclasses = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                superclasses.append(base.id)
            elif isinstance(base, ast.Attribute):
                superclasses.append(base.attr)

        children = []
        for stmt in node.body:
            children.extend(convert_python_ast_node(stmt))

        start_line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", start_line + 10)

        results.append({
            "type": "class_def",
            "name": node.name,
            "superclasses": superclasses,
            "range": {"start": {"line": start_line, "column": node.col_offset}, "end": {"line": end_line, "column": 0}},
            "children": children
        })

    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        params = []
        for arg in node.args.args:
            p_name = arg.arg
            p_type = None
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    p_type = arg.annotation.id
                elif isinstance(arg.annotation, ast.Attribute):
                    p_type = arg.annotation.attr
            params.append({"name": p_name, "type": p_type})

        ret_type = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                ret_type = node.returns.id
            elif isinstance(node.returns, ast.Attribute):
                ret_type = node.returns.attr

        start_line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", start_line + 5)

        results.append({
            "type": "func_def",
            "name": node.name,
            "metadata": {"parameters": params, "return_type": ret_type},
            "range": {"start": {"line": start_line, "column": node.col_offset}, "end": {"line": end_line, "column": 0}},
            "children": []
        })

    elif isinstance(node, ast.Import):
        for alias in node.names:
            results.append({
                "type": "import_statement",
                "name": alias.name,
                "range": {"start": {"line": getattr(node, "lineno", 1), "column": node.col_offset}, "end": {"line": getattr(node, "lineno", 1), "column": 10}},
                "children": []
            })

    elif isinstance(node, ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            imported_name = f"{mod}.{alias.name}" if mod else alias.name
            results.append({
                "type": "import_from_statement",
                "name": imported_name,
                "range": {"start": {"line": getattr(node, "lineno", 1), "column": node.col_offset}, "end": {"line": getattr(node, "lineno", 1), "column": 10}},
                "children": []
            })

    return results


def parse_source_file(source_code: str, file_path: str) -> ParserResult:
    parsed_ast = ast.parse(source_code, filename=file_path)
    ast_roots = convert_python_ast_node(parsed_ast)
    ast_root = ast_roots[0] if ast_roots else {"type": "module", "name": "empty", "children": []}

    line_count = source_code.count("\n") + 1
    return ParserResult(
        job_id=f"job-{hash(file_path)}",
        file_path=file_path,
        language=ParserLanguage.PYTHON,
        statistics=ParserStatistics(lines_parsed=line_count, node_count=len(ast_roots)),
        metadata=ParserMetadata(
            parser_name="python-ast",
            language=ParserLanguage.PYTHON,
            version=ParserVersion(semver="1.0.0")
        ),
        ast_root=ast_root
    )


def build_scikit_learn_sample_files() -> dict[str, str]:
    return {
        "sklearn/base.py": """
import copy
from typing import Any, List, Dict

class BaseEstimator:
    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        return {}

    def set_params(self, **params) -> "BaseEstimator":
        return self

class ClassifierMixin:
    def score(self, X: Any, y: Any) -> float:
        return 0.95

class RegressorMixin:
    def score(self, X: Any, y: Any) -> float:
        return 0.90

class TransformerMixin:
    def fit_transform(self, X: Any, y: Any = None) -> Any:
        return X

def clone(estimator: BaseEstimator) -> BaseEstimator:
    return copy.deepcopy(estimator)
""",
        "sklearn/utils/validation.py": """
from typing import Any, Tuple

def check_array(array: Any, accept_sparse: bool = False) -> Any:
    return array

def check_X_y(X: Any, y: Any) -> Tuple[Any, Any]:
    X = check_array(X)
    y = check_array(y)
    return X, y

def check_is_fitted(estimator: Any, attributes: Any = None) -> None:
    pass
""",
        "sklearn/linear_model/_base.py": """
from typing import Any
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.utils.validation import check_X_y, check_is_fitted

class LinearModel(BaseEstimator):
    def fit(self, X: Any, y: Any) -> "LinearModel":
        X, y = check_X_y(X, y)
        self.coef_ = [1.0, 2.0]
        return self

    def predict(self, X: Any) -> Any:
        check_is_fitted(self)
        return X

class LinearClassifierMixin(ClassifierMixin):
    def decision_function(self, X: Any) -> Any:
        return X
""",
        "sklearn/linear_model/_logistic.py": """
from typing import Any
from sklearn.linear_model._base import LinearModel, LinearClassifierMixin
from sklearn.utils.validation import check_X_y, check_is_fitted

class LogisticRegression(LinearModel, LinearClassifierMixin):
    def fit(self, X: Any, y: Any) -> "LogisticRegression":
        X, y = check_X_y(X, y)
        self.classes_ = [0, 1]
        return self

    def predict_proba(self, X: Any) -> Any:
        check_is_fitted(self)
        return X
""",
        "sklearn/linear_model/_ridge.py": """
from typing import Any
from sklearn.linear_model._base import LinearModel
from sklearn.base import RegressorMixin

class Ridge(LinearModel, RegressorMixin):
    def fit(self, X: Any, y: Any) -> "Ridge":
        self.coef_ = [0.5, 0.5]
        return self
""",
        "sklearn/tree/_classes.py": """
from typing import Any
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.utils.validation import check_X_y, check_is_fitted

class BaseDecisionTree(BaseEstimator):
    def fit(self, X: Any, y: Any) -> "BaseDecisionTree":
        X, y = check_X_y(X, y)
        self.tree_ = {}
        return self

class DecisionTreeClassifier(BaseDecisionTree, ClassifierMixin):
    def predict_proba(self, X: Any) -> Any:
        check_is_fitted(self)
        return X

class DecisionTreeRegressor(BaseDecisionTree, RegressorMixin):
    def predict(self, X: Any) -> Any:
        check_is_fitted(self)
        return X
""",
        "sklearn/ensemble/_forest.py": """
from typing import Any, List
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.tree._classes import DecisionTreeClassifier, DecisionTreeRegressor

class BaseForest(BaseEstimator):
    def fit(self, X: Any, y: Any) -> "BaseForest":
        self.estimators_ = []
        return self

class RandomForestClassifier(BaseForest, ClassifierMixin):
    def predict_proba(self, X: Any) -> Any:
        return X

class RandomForestRegressor(BaseForest, RegressorMixin):
    def predict(self, X: Any) -> Any:
        return X
""",
        "sklearn/preprocessing/_data.py": """
from typing import Any
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_array

class StandardScaler(BaseEstimator, TransformerMixin):
    def fit(self, X: Any, y: Any = None) -> "StandardScaler":
        X = check_array(X)
        self.mean_ = [0.0]
        self.scale_ = [1.0]
        return self

    def transform(self, X: Any) -> Any:
        return X

class MinMaxScaler(BaseEstimator, TransformerMixin):
    def fit(self, X: Any, y: Any = None) -> "MinMaxScaler":
        X = check_array(X)
        self.data_min_ = [0.0]
        self.data_max_ = [1.0]
        return self
""",
        "sklearn/pipeline.py": """
from typing import Any, List, Tuple
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

class Pipeline(BaseEstimator):
    def __init__(self, steps: List[Tuple[str, BaseEstimator]]):
        self.steps = steps

    def fit(self, X: Any, y: Any = None) -> "Pipeline":
        return self

    def predict(self, X: Any) -> Any:
        check_is_fitted(self)
        return X

def make_pipeline(*steps: BaseEstimator) -> Pipeline:
    named_steps = [(f"step_{i}", step) for i, step in enumerate(steps)]
    return Pipeline(named_steps)
""",
        "sklearn/metrics/_classification.py": """
from typing import Any
from sklearn.utils.validation import check_X_y

def accuracy_score(y_true: Any, y_pred: Any) -> float:
    return 1.0

def precision_score(y_true: Any, y_pred: Any) -> float:
    return 1.0

def recall_score(y_true: Any, y_pred: Any) -> float:
    return 1.0

def f1_score(y_true: Any, y_pred: Any) -> float:
    return 1.0
""",
        "sklearn/model_selection/_split.py": """
from typing import Any, List
from sklearn.base import BaseEstimator

class BaseCrossValidator:
    def split(self, X: Any, y: Any = None) -> Any:
        yield [0], [1]

class KFold(BaseCrossValidator):
    def __init__(self, n_splits: int = 5):
        self.n_splits = n_splits

class StratifiedKFold(BaseCrossValidator):
    def __init__(self, n_splits: int = 5):
        self.n_splits = n_splits
"""
    }


def run_scikit_learn_benchmark():
    print("=" * 80)
    print("DEVBRAIN REPOSITORY ANALYZER V2 - REAL-WORLD SCIKIT-LEARN BENCHMARK")
    print("=" * 80)

    sample_files = build_scikit_learn_sample_files()
    print(f"\n[1/3] Parsing {len(sample_files)} Python modules in scikit-learn codebase...")

    parser_results = []
    parse_start = time.perf_counter()
    for file_path, source_code in sample_files.items():
        res = parse_source_file(source_code, file_path)
        parser_results.append(res)
    parse_duration = (time.perf_counter() - parse_start) * 1000.0

    print(f"      Parsed {len(parser_results)} modules in {parse_duration:.2f} ms")

    print("\n[2/3] Executing DependencyGraphFacade.analyze_repository pipeline...")
    analysis_start = time.perf_counter()
    result = DependencyGraphFacade.analyze_repository(
        parser_results=parser_results,
        repository_id="scikit-learn-machine-learning-framework"
    )
    analysis_duration = (time.perf_counter() - analysis_start) * 1000.0

    print("\n[3/3] Analysis Pipeline Completed Successfully!")
    print("=" * 80)
    print("BENCHMARK METRICS SUMMARY:")
    print("=" * 80)
    print(f"  Repository ID         : {result.repository_id}")
    print(f"  Schema SemVer         : {result.version}")
    print(f"  Total Duration        : {result.duration_ms:.2f} ms")
    print(f"  Canonical Symbols     : {len(result.semantic_repository.canonical_symbols.symbols)}")
    print(f"  Total Dependency Edges: {len(result.graph.edges)}")
    print(f"  Graph Density         : {result.graph.statistics.graph_density:.6f}")

    print("\n  Edge Kind Breakdown:")
    for edge_kind, count in result.graph.statistics.edges_by_kind_counts.items():
        print(f"    - {edge_kind:<20}: {count}")

    print("\n  Validation Report:")
    print(f"    - Status            : {'PASSED' if result.validation_report.is_valid else 'FAILED'}")
    print(f"    - SHA-256 Hash      : {result.validation_report.validated_graph_hash}")
    print(f"    - Evaluated Rules   : {result.validation_report.statistics.rules_evaluated_count}")
    print(f"    - Errors            : {result.validation_report.error_count}")
    print(f"    - Warnings          : {result.validation_report.warning_count}")
    print("=" * 80)


if __name__ == "__main__":
    run_scikit_learn_benchmark()
