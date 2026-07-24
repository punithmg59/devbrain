"""
scratch/diagnose_unresolved.py
-------------------------------
Diagnostic script: loads the fastapi_analysis_data.json and inspects
the import errors to categorize UNRESOLVED_MODULE vs UNRESOLVED_SYMBOL,
plus check what modules are registered and whether re-export paths are hit.
"""

import json
import sys
import os
from collections import defaultdict

sys.path.insert(0, r"d:\devbrain\backend\repository_analyzer_v2")

# Read saved analysis data for import errors
data_file = r"d:\devbrain\scratch\fastapi_analysis_data.json"
with open(data_file, "r") as f:
    data = json.load(f)

errors = data.get("import_errors", [])
print(f"Total import errors: {len(errors)}")
print()

# Categorize
module_errors = [e for e in errors if "Relative module" in e or "could not be resolved in repository" in e]
symbol_errors = [e for e in errors if "not found in module" in e]
other_errors = [e for e in errors if e not in module_errors and e not in symbol_errors]

print(f"UNRESOLVED_MODULE errors: {len(module_errors)}")
print(f"UNRESOLVED_SYMBOL errors: {len(symbol_errors)}")
print(f"Other errors: {len(other_errors)}")
print()

if module_errors:
    print("=== Sample UNRESOLVED_MODULE errors (first 20) ===")
    for e in module_errors[:20]:
        print(f"  {e}")
    print()

if symbol_errors:
    print("=== Sample UNRESOLVED_SYMBOL errors (first 20) ===")
    for e in symbol_errors[:20]:
        print(f"  {e}")
    print()

if other_errors:
    print("=== Other errors (first 10) ===")
    for e in other_errors[:10]:
        print(f"  {e}")
    print()

# Now run a fresh targeted analysis to understand path registration
print("=== Running targeted module registration check ===")
from plugins.python.python_parser_plugin import PythonParserPlugin
from plugins.python.semantic_extractor import PythonSemanticExtractor
from analysis.import_resolution.module_index import ModuleIndex
from analysis.re_export_resolution.re_export_builder import ReExportBuilder
from core.execution_context import ExecutionContext
from models.job import AnalysisJob
from models.repository import RepositoryFile

repo_path = r"d:\devbrain\fastapi"

# Read just fastapi/__init__.py and fastapi/applications.py
targets = [
    "fastapi/__init__.py",
    "fastapi/applications.py",
    "fastapi/routing.py",
]

python_plugin = PythonParserPlugin()
python_plugin.initialize()
semantic_extractor = PythonSemanticExtractor()

sem_results = []
for rel_path in targets:
    abs_path = os.path.join(repo_path, rel_path)
    if not os.path.exists(abs_path):
        print(f"  MISSING: {rel_path}")
        continue
    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
        source = f.read()

    job = AnalysisJob(
        repository_id="fastapi_repo",
        file=RepositoryFile(
            path=rel_path,
            name=os.path.basename(rel_path),
            extension="py",
            language="python",
            size_bytes=len(source),
            line_count=source.count("\n") + 1,
            content=source,
        ),
        language="python",
    )
    ctx = ExecutionContext(job=job, worker=None, pipeline_context=None)
    parse_result = python_plugin.parse(job, ctx)
    sem_res = semantic_extractor.extract_result(parse_result)
    sem_results.append(sem_res)

    print(f"\n--- {rel_path} ---")
    print(f"  module.name = {sem_res.module.name!r}")
    print(f"  file_path   = {sem_res.file_path!r}")
    print(f"  imports ({len(sem_res.module.imports)}):")
    for imp in sem_res.module.imports[:10]:
        print(f"    module={imp.module!r}  names={imp.imported_names}  rel={imp.is_relative}  level={imp.relative_level}")

# Build module index and check what gets registered
module_index = ModuleIndex()
for res in sem_results:
    module_index.register_file(res.file_path, res.module.name)

print(f"\n=== Module Index Registration ===")
for fp, fqn in module_index.file_path_to_fqn.items():
    print(f"  {fp!r} → {fqn!r}")

# Build re-export index
builder = ReExportBuilder()
records = builder.build_from_results(sem_results, module_index)
print(f"\n=== ReExportBuilder found {len(records)} export records ===")
for rec in records:
    print(f"  pkg={rec.package_fqn!r}  name={rec.exported_name!r}  src={rec.source_module_fqn!r}  type={rec.export_type}")

# Simulate resolving `from fastapi import FastAPI`
print("\n=== Simulating 'from fastapi import FastAPI' resolution ===")
from analysis.re_export_resolution.re_export_index import ReExportIndex
from analysis.re_export_resolution.re_export_resolver import ReExportResolver
from analysis.symbol_table.symbol_builder import SymbolTableBuilder

sym_builder = SymbolTableBuilder(repository_id="fastapi_repo")
symbol_table = sym_builder.build_from_results(sem_results)

export_index = ReExportIndex()
export_index.build(records)

resolver = ReExportResolver()
sym, fqn = resolver.resolve("fastapi", "FastAPI", export_index, symbol_table)
print(f"  FastAPI → sym={sym}, fqn={fqn!r}")

sym2, fqn2 = resolver.resolve("fastapi", "APIRouter", export_index, symbol_table)
print(f"  APIRouter → sym={sym2}, fqn={fqn2!r}")

# Check what package FQNs are in the index
print(f"\n=== Export index packages: {export_index.all_package_fqns()} ===")
print(f"  Named lookups sample:")
for (pkg, name), rec in list(export_index._named.items())[:10]:
    print(f"    ({pkg!r}, {name!r}) → src={rec.source_module_fqn!r}")
