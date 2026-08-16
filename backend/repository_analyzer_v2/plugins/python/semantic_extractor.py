"""
plugins/python/semantic_extractor.py
------------------------------------
Phase 4.3 — Python Semantic Extractor.

Converts a DevBrain AST (`ASTRoot` / `ASTNode`) or `ParserResult` into language-independent
structured semantic entities (`SemanticExtractionResult`).

Design Principles
-----------------
- **Independent from Parser Backend**: Operates strictly on `ASTRoot` and `ASTNode` data models.
  Does NOT import or interact with Tree-sitter or C bindings.
- **Single-Pass AST Traversal**: Traverses the AST in a single recursive walk, maintaining a
  scope context stack for lexical nesting and enclosing containers.
- **High Performance**: Direct tree navigation, minimal memory allocations, targeting <5ms per
  file execution duration.
- **Robust Error Recovery**: Handles malformed nodes, missing names, and syntax error trees gracefully.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from models.ast import ASTNode, ASTRoot, NodeRange, NodeType
from models.parser import ParserResult
from models.semantic import (
    ExtractedClass,
    ExtractedDecorator,
    ExtractedFunction,
    ExtractedImport,
    ExtractedParameter,
    ExtractedVariable,
    MethodModifier,
    ParameterKind,
    SemanticExtractionResult,
    SemanticMetrics,
    VariableScope,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Regex for uppercase constant naming convention (e.g. MAX_RETRIES, DEBUG, DEFAULT_TIMEOUT)
CONSTANT_NAME_REGEX = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _is_constant_name(name: str) -> bool:
    """Return True if symbol name follows uppercase constant naming convention."""
    if not name or name.startswith("__"):
        return False
    return bool(CONSTANT_NAME_REGEX.match(name))


def _parse_decorator_expression(dec_str: str, range_obj: Optional[NodeRange] = None) -> ExtractedDecorator:
    """
    Parse a decorator string (e.g. '@app.get("/users/{id}")', '@staticmethod') into ExtractedDecorator.
    """
    raw = dec_str.strip()
    expr = raw if raw.startswith("@") else f"@{raw}"
    body = expr[1:].strip()

    name = body
    arguments: List[str] = []

    paren_idx = body.find("(")
    if paren_idx != -1 and body.endswith(")"):
        name = body[:paren_idx].strip()
        args_raw = body[paren_idx + 1 : -1].strip()
        if args_raw:
            arguments = [a.strip() for a in args_raw.split(",")]

    return ExtractedDecorator(
        expression=expr,
        name=name,
        arguments=arguments,
        range=range_obj,
    )


def _extract_api_route_info(decorators: List[ExtractedDecorator]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract HTTP method and route path from decorators if this is an API route.
    
    Supports FastAPI/Flask patterns like:
    - @app.get("/users")
    - @router.post("/users/{id}")
    - @api_router.put("/items")
    - @delete("/items/{item_id}")
    
    Returns (http_method, route_path) or (None, None) if not an API route.
    """
    http_methods = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}
    
    for decorator in decorators:
        # Pattern 1: @app.get("/path"), @router.post("/path")
        if "." in decorator.name:
            parts = decorator.name.split(".")
            method = parts[-1].lower()
            if method in http_methods and decorator.arguments:
                # Extract route path from first argument (usually a string)
                route_arg = decorator.arguments[0] if decorator.arguments else ""
                # Remove quotes from the route path
                route_path = route_arg.strip('"\'')
                if route_path:
                    return method.upper(), route_path
        
        # Pattern 2: @get("/path"), @post("/path") (direct method decorators)
        method = decorator.name.lower()
        if method in http_methods and decorator.arguments:
            route_arg = decorator.arguments[0] if decorator.arguments else ""
            route_path = route_arg.strip('"\'')
            if route_path:
                return method.upper(), route_path
    
    return None, None


def _infer_expression_kind(node: ASTNode) -> str:
    """Determine syntactic kind of an assigned expression node."""
    if not node.children:
        if node.type == NodeType.LITERAL:
            return "literal"
        if node.type == NodeType.IDENTIFIER:
            return "identifier"
        return "unknown"

    for child in node.children:
        if child.type == NodeType.LITERAL:
            return "literal"
        if child.type == NodeType.CALL:
            return "call"
        if child.type in (NodeType.BINARY_OP, NodeType.UNARY_OP):
            return "binary_op"
        if child.type == NodeType.IDENTIFIER:
            return "identifier"
        if child.type in (NodeType.EXPRESSION, NodeType.STATEMENT):
            return _infer_expression_kind(child)

    return "unknown"


def _check_is_generator(node: ASTNode) -> bool:
    """Return True if node or any descendant contains yield / yield from."""
    for n in node.walk():
        if n.value and "yield" in n.value:
            return True
        if n.name and "yield" in n.name:
            return True
    return False


class PythonSemanticExtractor:
    """
    Single-pass semantic extractor for Python source files.

    Translates an `ASTRoot` tree into an `ExtractedModule` entity hierarchy.

    Usage::

        extractor = PythonSemanticExtractor()
        result = extractor.extract(ast_root)
    """

    def __init__(self) -> None:
        self._warnings: List[str] = []
        self._errors: List[str] = []

    def extract_result(self, parser_result: ParserResult) -> SemanticExtractionResult:
        """
        Extract semantic entities from a `ParserResult`.

        Parameters
        ----------
        parser_result:
            The `ParserResult` returned by `PythonParserPlugin.parse()`.

        Returns
        -------
        SemanticExtractionResult
            Extracted semantic entity tree and metadata metrics.
        """
        if parser_result.ast_root is None:
            module_name = self._derive_module_name(parser_result.file_path)
            from models.semantic import ExtractedModule
            empty_module = ExtractedModule(
                name=module_name,
                file_path=parser_result.file_path,
            )
            return SemanticExtractionResult(
                file_path=parser_result.file_path,
                language="python",
                module=empty_module,
                metrics=SemanticMetrics(extraction_duration_ms=0.0),
                warnings=["ParserResult contains no AST root"],
            )

        ast_root = ASTRoot.model_validate(parser_result.ast_root)
        return self.extract(ast_root, parser_result=parser_result)

    def extract(
        self,
        ast_root: ASTRoot,
        parser_result: Optional[ParserResult] = None,
    ) -> SemanticExtractionResult:
        """
        Extract semantic entities from an `ASTRoot`.

        Parameters
        ----------
        ast_root:
            The DevBrain `ASTRoot` to process.
        parser_result:
            Optional `ParserResult` metadata context.

        Returns
        -------
        SemanticExtractionResult
        """
        start_time = time.perf_counter()
        self._warnings.clear()
        self._errors.clear()

        module_name = self._derive_module_name(ast_root.file_path)
        module_docstring = ast_root.root_node.metadata.docstring

        from models.semantic import ExtractedModule
        module = ExtractedModule(
            name=module_name,
            file_path=ast_root.file_path,
            docstring=module_docstring,
        )

        # Traverse AST children of root node (module level)
        for node in ast_root.root_node.children:
            self._process_node(
                node=node,
                module=module,
                class_context=None,
                func_context=None,
                nesting_level=0,
            )

        # Count extracted entities
        import_count = len(module.imports)
        class_count = len(module.classes)
        function_count = len(module.functions)
        variable_count = len(module.global_variables)
        constant_count = len(module.constants)

        for cls in module.classes:
            function_count += len(cls.methods)
            variable_count += len(cls.class_attributes)

        for fn in module.functions:
            variable_count += len(fn.local_variables)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        memory_bytes = self._get_memory_bytes()

        metrics = SemanticMetrics(
            extraction_duration_ms=round(duration_ms, 3),
            module_count=1,
            class_count=class_count,
            function_count=function_count,
            import_count=import_count,
            variable_count=variable_count,
            constant_count=constant_count,
            memory_rss_bytes=memory_bytes,
        )

        logger.debug(
            f"[PythonSemanticExtractor] Extracted '{ast_root.file_path}' in {duration_ms:.2f}ms "
            f"(classes={class_count}, funcs={function_count}, imports={import_count})"
        )

        return SemanticExtractionResult(
            file_path=ast_root.file_path,
            language="python",
            module=module,
            metrics=metrics,
            warnings=list(self._warnings),
            errors=list(self._errors),
        )

    # ------------------------------------------------------------------
    # Scope & Node Processors
    # ------------------------------------------------------------------

    def _process_node(
        self,
        node: ASTNode,
        module: ExtractedModule,
        class_context: Optional[ExtractedClass],
        func_context: Optional[ExtractedFunction],
        nesting_level: int,
    ) -> None:
        """Process an AST node within its current lexical scope context."""
        ntype = node.type

        # 1. IMPORTS
        if ntype == NodeType.IMPORT:
            imp = self._extract_import(node)
            if imp:
                module.imports.append(imp)
            return

        # 2. CLASSES
        if ntype == NodeType.CLASS:
            cls = self._extract_class(
                node,
                module=module,
                nesting_level=nesting_level,
                parent_class=class_context.name if class_context else None,
            )
            module.classes.append(cls)
            return

        # 3. FUNCTIONS
        if ntype == NodeType.FUNCTION:
            fn = self._extract_function(
                node,
                module=module,
                nesting_level=nesting_level,
                enclosing_class=class_context.name if class_context else None,
                enclosing_function=func_context.name if func_context else None,
            )
            module.functions.append(fn)
            if class_context:
                class_context.methods.append(fn)
            return

        # 4. ASSIGNMENTS (Variables / Constants)
        if ntype == NodeType.ASSIGNMENT:
            var = self._extract_variable(
                node,
                scope=VariableScope.GLOBAL if not class_context and not func_context
                else (VariableScope.CLASS_ATTRIBUTE if class_context and not func_context else VariableScope.LOCAL)
            )
            if var:
                if class_context and not func_context:
                    class_context.class_attributes.append(var)
                elif func_context:
                    func_context.local_variables.append(var)
                else:
                    if var.is_constant:
                        module.constants.append(var)
                    else:
                        module.global_variables.append(var)
            return

        # 5. BLOCK / STATEMENTS / EXPRESSIONS — Recurse into children
        for child in node.children:
            self._process_node(
                child,
                module=module,
                class_context=class_context,
                func_context=func_context,
                nesting_level=nesting_level,
            )

    # ------------------------------------------------------------------
    # Entity Extractors
    # ------------------------------------------------------------------

    def _extract_import(self, node: ASTNode) -> Optional[ExtractedImport]:
        """Extract `ExtractedImport` from an `IMPORT` AST node."""
        raw_name = (node.name or node.value or "").strip()
        if not raw_name:
            return None

        module: Optional[str] = None
        imported_names: List[str] = []
        aliases: Dict[str, str] = {}
        is_relative = False
        relative_level = 0

        # Case A: "from ..." statement
        if raw_name.startswith("from "):
            body = raw_name[5:]
            if " import " in body:
                mod_part, names_part = body.split(" import ", 1)
                mod_part, names_part = mod_part.strip(), names_part.strip()

                dot_match = re.match(r"^(\.+)(.*)", mod_part)
                if dot_match:
                    is_relative = True
                    relative_level = len(dot_match.group(1))
                    rem = dot_match.group(2).strip()
                    module = rem if rem else None
                else:
                    module = mod_part

                for item in names_part.split(","):
                    item = item.strip()
                    if not item:
                        continue
                    if " as " in item:
                        orig, alias = item.split(" as ", 1)
                        orig, alias = orig.strip(), alias.strip()
                        imported_names.append(orig)
                        aliases[orig] = alias
                    else:
                        imported_names.append(item)

                if node.metadata and node.metadata.custom:
                    if "aliases" in node.metadata.custom and node.metadata.custom["aliases"]:
                        aliases.update(node.metadata.custom["aliases"])
                    if "imported_names" in node.metadata.custom and not imported_names:
                        imported_names = list(node.metadata.custom["imported_names"])

                return ExtractedImport(
                    module=module,
                    imported_names=imported_names,
                    aliases=aliases,
                    is_relative=is_relative,
                    relative_level=relative_level,
                    range=node.range,
                )

        # Case B: "import ..." statement or plain module name
        clean = raw_name
        if clean.startswith("import "):
            clean = clean[7:].strip()

        for item in clean.split(","):
            item = item.strip()
            if not item:
                continue
            if " as " in item:
                orig, alias = item.split(" as ", 1)
                orig, alias = orig.strip(), alias.strip()
                imported_names.append(orig)
                aliases[orig] = alias
                if module is None:
                    module = orig
            else:
                imported_names.append(item)
                if module is None:
                    module = item

        # Check custom metadata from native AST or TreeSitter converter
        if node.metadata and node.metadata.custom:
            custom_names = node.metadata.custom.get("imported_names")
            custom_aliases = node.metadata.custom.get("aliases")
            custom_module = node.metadata.custom.get("module")
            if custom_names and not imported_names:
                imported_names = list(custom_names)
            if custom_aliases:
                aliases.update(custom_aliases)
            if custom_module and not module:
                module = custom_module

        return ExtractedImport(
            module=module,
            imported_names=imported_names,
            aliases=aliases,
            is_relative=is_relative,
            relative_level=relative_level,
            range=node.range,
        )

    def _extract_class(
        self,
        node: ASTNode,
        module: ExtractedModule,
        nesting_level: int,
        parent_class: Optional[str],
    ) -> ExtractedClass:
        """Extract `ExtractedClass` entity from a `CLASS` AST node."""
        name = node.name or "UnknownClass"
        docstring = node.metadata.docstring

        # Decorators
        decorators = [
            _parse_decorator_expression(d, range_obj=node.range)
            for d in node.metadata.decorators
        ]

        # Base classes from custom metadata or children
        base_classes: List[str] = list(node.metadata.custom.get("base_classes", []))
        if not base_classes:
            for child in node.children:
                if child.type in (NodeType.IDENTIFIER, NodeType.EXPRESSION, NodeType.CALL) and child.name:
                    if child.name != name:
                        base_classes.append(child.name)

        cls = ExtractedClass(
            name=name,
            docstring=docstring,
            decorators=decorators,
            base_classes=base_classes,
            range=node.range,
            nesting_level=nesting_level,
            parent_class=parent_class,
        )

        # Process class body members (methods, attributes, nested classes)
        for child in node.children:
            self._process_node(
                node=child,
                module=module,
                class_context=cls,
                func_context=None,
                nesting_level=nesting_level + 1,
            )

        return cls

    def _extract_function(
        self,
        node: ASTNode,
        module: ExtractedModule,
        nesting_level: int,
        enclosing_class: Optional[str],
        enclosing_function: Optional[str],
    ) -> ExtractedFunction:
        """Extract `ExtractedFunction` entity from a `FUNCTION` AST node."""
        name = node.name or "<anonymous>"
        is_async = "async" in node.metadata.modifiers
        docstring = node.metadata.docstring
        return_annotation = node.metadata.type_annotation

        # Decorators
        decorators = [
            _parse_decorator_expression(d, range_obj=node.range)
            for d in node.metadata.decorators
        ]

        # Extract API route information if this is an API endpoint
        http_method, route_path = _extract_api_route_info(decorators)

        # Method modifiers
        method_modifiers = self._determine_method_modifiers(decorators, enclosing_class)

        # Parameters
        parameters = self._extract_parameters(node)

        # Generator check
        is_generator = _check_is_generator(node)

        fn = ExtractedFunction(
            name=name,
            is_async=is_async,
            decorators=decorators,
            parameters=parameters,
            return_annotation=return_annotation,
            docstring=docstring,
            range=node.range,
            nesting_level=nesting_level,
            enclosing_class=enclosing_class,
            enclosing_function=enclosing_function,
            method_modifiers=method_modifiers,
            is_generator=is_generator,
            http_method=http_method,
            route_path=route_path,
        )

        # Process function body (local variables and nested functions)
        for child in node.children:
            self._process_node(
                node=child,
                module=module,
                class_context=None,
                func_context=fn,
                nesting_level=nesting_level + 1,
            )

        return fn

    def _determine_method_modifiers(
        self,
        decorators: List[ExtractedDecorator],
        enclosing_class: Optional[str],
    ) -> List[MethodModifier]:
        """Determine method modifiers (instance, static, class, property, abstract)."""
        if not enclosing_class:
            return []

        modifiers: List[MethodModifier] = []

        dec_names = {d.name for d in decorators}
        if "staticmethod" in dec_names:
            modifiers.append(MethodModifier.STATIC)
        elif "classmethod" in dec_names:
            modifiers.append(MethodModifier.CLASS)
        elif any(d in dec_names or d.endswith(".setter") or d.endswith(".deleter") for d in ("property",)):
            modifiers.append(MethodModifier.PROPERTY)
        else:
            modifiers.append(MethodModifier.INSTANCE)

        if "abstractmethod" in dec_names or any("abstract" in d for d in dec_names):
            modifiers.append(MethodModifier.ABSTRACT)

        return modifiers

    def _extract_parameters(self, func_node: ASTNode) -> List[ExtractedParameter]:
        """Extract parameter list from a function AST node."""
        params: List[ExtractedParameter] = []

        param_nodes = func_node.find_by_type(NodeType.PARAMETER)
        for pnode in param_nodes:
            pname = pnode.name or "arg"
            annotation = pnode.metadata.type_annotation
            has_default = pnode.value is not None
            default_val = pnode.value

            kind = ParameterKind.POSITIONAL
            if pname.startswith("**"):
                kind = ParameterKind.VAR_KEYWORD
                pname = pname[2:]
            elif pname.startswith("*"):
                kind = ParameterKind.VAR_POSITIONAL
                pname = pname[1:]
            elif has_default:
                kind = ParameterKind.KEYWORD

            params.append(
                ExtractedParameter(
                    name=pname,
                    annotation=annotation,
                    has_default=has_default,
                    default_value=default_val,
                    kind=kind,
                )
            )

        return params

    def _extract_variable(
        self,
        node: ASTNode,
        scope: VariableScope,
    ) -> Optional[ExtractedVariable]:
        """Extract `ExtractedVariable` entity from an `ASSIGNMENT` AST node."""
        name = node.name
        if not name:
            return None

        annotation = node.metadata.type_annotation
        inferred_kind = _infer_expression_kind(node)
        is_const = _is_constant_name(name)
        value_snippet = node.value

        return ExtractedVariable(
            name=name,
            scope=scope,
            annotation=annotation,
            inferred_expression_kind=inferred_kind,
            is_constant=is_const,
            value_snippet=value_snippet,
            range=node.range,
        )

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_module_name(file_path: str) -> str:
        """Derive python module dot-name from file path, e.g. 'src/utils/helpers.py' -> 'utils.helpers'."""
        clean = file_path.replace("\\", "/")
        if clean.endswith(".py"):
            clean = clean[:-3]
        elif clean.endswith(".pyi"):
            clean = clean[:-4]

        parts = [p for p in clean.split("/") if p and p != "src"]
        return ".".join(parts) if parts else "module"

    @staticmethod
    def _get_memory_bytes() -> int:
        try:
            import psutil
            return psutil.Process(os.getpid()).memory_info().rss
        except Exception:
            return 0
