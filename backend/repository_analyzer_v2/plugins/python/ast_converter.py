"""
plugins/python/ast_converter.py
--------------------------------
Phase 4.2 — Python ParseTree → DevBrain AST Converter.

Responsibility
--------------
Converts a ``ParseTree`` (the tree-sitter-engine boundary wrapper produced
by ``TreeSitterEngine.parse()``) into a fully populated ``ASTRoot`` /
``ASTNode`` tree — DevBrain's parser-independent intermediate representation.

Design Principles
-----------------
- **No native tree-sitter objects**: All conversion input is the serializable
  ``ParseTreeNode`` model.  This module never touches ``tree_sitter.Node``.
- **Faithful structure**: Every node in the parse tree maps to at least one
  ``ASTNode``.  Non-informative anonymous tokens (punctuation, keywords) are
  collapsed into parent metadata rather than emitted as separate children.
- **Rich semantic enrichment**: Named constructs (functions, classes, imports)
  receive name extraction, type annotation, modifier detection, and docstring
  extraction beyond what the raw tree carries.
- **Error resilience**: ERROR / MISSING nodes are mapped to ``NodeType.UNKNOWN``
  and do not abort conversion.

Node Type Mapping
-----------------
The ``_NODE_TYPE_MAP`` dictionary maps Tree-sitter grammar node types to
DevBrain ``NodeType`` enum values.  Anything not in the map falls back to
``NodeType.STATEMENT`` (for named nodes) or is skipped (for anonymous tokens).

Name Extraction Strategy
------------------------
Each named construct type implements a targeted ``_extract_*_name`` helper
that reads the node's ``children`` for the ``identifier`` child that names
the symbol.  This avoids ad-hoc string parsing of raw source.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Set, Tuple

from models.ast import ASTNode, ASTRoot, NodeLocation, NodeMetadata, NodeRange, NodeType
from models.tree_sitter_models import ParseTree, ParseTreeNode
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Grammar node type → DevBrain NodeType mapping
# ---------------------------------------------------------------------------

#: Named node types we want to preserve as meaningful AST nodes.
_NODE_TYPE_MAP: Dict[str, NodeType] = {
    # Top-level structure
    "module":                      NodeType.MODULE,
    # Definitions
    "function_definition":         NodeType.FUNCTION,
    "async_function_definition":   NodeType.FUNCTION,   # alias in some grammar versions
    "class_definition":            NodeType.CLASS,
    "decorated_definition":        NodeType.FUNCTION,   # resolved to inner type during walk
    # Parameters
    "parameters":                  NodeType.BLOCK,
    "parameter":                   NodeType.PARAMETER,
    "typed_parameter":             NodeType.PARAMETER,
    "default_parameter":           NodeType.PARAMETER,
    "typed_default_parameter":     NodeType.PARAMETER,
    "list_splat_pattern":          NodeType.PARAMETER,
    "dictionary_splat_pattern":    NodeType.PARAMETER,
    "keyword_separator":           NodeType.PARAMETER,
    "positional_separator":        NodeType.PARAMETER,
    # Imports
    "import_statement":            NodeType.IMPORT,
    "import_from_statement":       NodeType.IMPORT,
    "future_import_statement":     NodeType.IMPORT,
    # Assignments / variables
    "assignment":                  NodeType.ASSIGNMENT,
    "augmented_assignment":        NodeType.ASSIGNMENT,
    "named_expression":            NodeType.ASSIGNMENT,
    "expression_statement":        NodeType.STATEMENT,
    # Control flow
    "if_statement":                NodeType.IF,
    "elif_clause":                 NodeType.IF,
    "else_clause":                 NodeType.ELSE,
    "for_statement":               NodeType.LOOP,
    "while_statement":             NodeType.LOOP,
    "match_statement":             NodeType.STATEMENT,
    "case_clause":                 NodeType.STATEMENT,
    # Exception handling
    "try_statement":               NodeType.TRY,
    "except_clause":               NodeType.CATCH,
    "except_group_clause":         NodeType.CATCH,
    "finally_clause":              NodeType.BLOCK,
    # Context managers
    "with_statement":              NodeType.STATEMENT,
    "with_clause":                 NodeType.BLOCK,
    # Returns / yields / awaits
    "return_statement":            NodeType.RETURN,
    "yield":                       NodeType.STATEMENT,
    "yield_statement":             NodeType.STATEMENT,
    "await":                       NodeType.STATEMENT,
    # Calls
    "call":                        NodeType.CALL,
    # Operators
    "binary_operator":             NodeType.BINARY_OP,
    "boolean_operator":            NodeType.BINARY_OP,
    "comparison_operator":         NodeType.BINARY_OP,
    "augmented_assignment":        NodeType.ASSIGNMENT,
    "unary_operator":              NodeType.UNARY_OP,
    "not_operator":                NodeType.UNARY_OP,
    # Identifiers / literals
    "identifier":                  NodeType.IDENTIFIER,
    "string":                      NodeType.LITERAL,
    "integer":                     NodeType.LITERAL,
    "float":                       NodeType.LITERAL,
    "true":                        NodeType.LITERAL,
    "false":                       NodeType.LITERAL,
    "none":                        NodeType.LITERAL,
    "concatenated_string":         NodeType.LITERAL,
    # Collections
    "list":                        NodeType.EXPRESSION,
    "tuple":                       NodeType.EXPRESSION,
    "set":                         NodeType.EXPRESSION,
    "dictionary":                  NodeType.EXPRESSION,
    "list_comprehension":          NodeType.EXPRESSION,
    "set_comprehension":           NodeType.EXPRESSION,
    "dictionary_comprehension":    NodeType.EXPRESSION,
    "generator_expression":        NodeType.EXPRESSION,
    # Attribute access
    "attribute":                   NodeType.EXPRESSION,
    "subscript":                   NodeType.EXPRESSION,
    # Lambda
    "lambda":                      NodeType.FUNCTION,
    # Type annotations
    "type":                        NodeType.TYPE_ANNOTATION,
    "type_alias_statement":        NodeType.TYPE_ANNOTATION,
    # Comments
    "comment":                     NodeType.COMMENT,
    # Blocks
    "block":                       NodeType.BLOCK,
    # Decorators
    "decorator":                   NodeType.EXPRESSION,
    # Misc patterns
    "pattern_list":                NodeType.EXPRESSION,
    "tuple_pattern":               NodeType.EXPRESSION,
    "as_pattern":                  NodeType.EXPRESSION,
    "ERROR":                       NodeType.UNKNOWN,
}

#: Anonymous token types that we skip when building children arrays.
_SKIP_ANONYMOUS: Set[str] = {
    ":", ",", "(", ")", "[", "]", "{", "}", "=", "->", ".", "@",
    "def", "class", "import", "from", "return", "yield", "await",
    "if", "elif", "else", "for", "while", "with", "try", "except",
    "finally", "async", "lambda", "in", "not", "and", "or", "as",
    "pass", "break", "continue", "global", "nonlocal", "del",
    "raise", "assert", "match", "case",
    "+", "-", "*", "/", "//", "%", "**", "&", "|", "^", "~",
    "<<", ">>", "==", "!=", "<", ">", "<=", ">=", "+=", "-=",
    "*=", "/=", "//=", "%=", "**=", "&=", "|=", "^=", "<<=", ">>=",
}


# ---------------------------------------------------------------------------
# Name extraction helpers
# ---------------------------------------------------------------------------

def _child_text(node: ParseTreeNode, child_type: str) -> Optional[str]:
    """Return the text of the first child with the given node_type."""
    for child in node.children:
        if child.node_type == child_type and child.text is not None:
            return child.text
    return None


def _first_named_child(node: ParseTreeNode, *types: str) -> Optional[ParseTreeNode]:
    """Return the first child whose node_type is in ``types``."""
    for child in node.children:
        if child.node_type in types:
            return child
    return None


def _relative_import_name(node: ParseTreeNode) -> str:
    """Extract name for relative_import node including leading dots."""
    dots = ""
    mod_name = ""
    for child in node.children:
        if child.node_type == "import_prefix":
            dots += child.text if child.text else "."
        elif child.node_type == "dotted_name":
            mod_name = _dotted_name(child)
        elif child.node_type == "identifier" and child.text:
            mod_name = child.text
    if not dots and node.text:
        dots = "".join(c for c in node.text if c == ".")
    return f"{dots}{mod_name}"


def _aliased_import_name(node: ParseTreeNode) -> str:
    """Return 'name as alias' for an aliased_import node."""
    name: Optional[str] = None
    alias: Optional[str] = None
    for child in node.children:
        if child.node_type == "dotted_name":
            if name is None:
                name = _dotted_name(child)
            else:
                alias = _dotted_name(child)
        elif child.node_type == "identifier" and child.text:
            if name is None:
                name = child.text
            else:
                alias = child.text

    if name and alias:
        return f"{name} as {alias}"
    return name or ""


def _extract_name(node: ParseTreeNode, ts_type: str) -> Optional[str]:
    """
    Extract the human-readable name for a named definition node.

    Strategy depends on node type.  For function / class definitions we look
    for the ``identifier`` child that immediately follows the ``def`` / ``class``
    keyword.  For imports we build a dotted-name string.
    """
    if ts_type in ("function_definition", "async_function_definition", "class_definition"):
        return _child_text(node, "identifier")

    if ts_type in ("parameter", "typed_parameter", "default_parameter", "typed_default_parameter"):
        return _child_text(node, "identifier")

    if ts_type == "list_splat_pattern":
        name = _child_text(node, "identifier")
        return f"*{name}" if name else "*"

    if ts_type == "dictionary_splat_pattern":
        name = _child_text(node, "identifier")
        return f"**{name}" if name else "**"

    if ts_type == "decorated_definition":
        # Inner definition is last child
        for child in node.children:
            if child.node_type in ("function_definition", "class_definition"):
                return _child_text(child, "identifier")
        return None

    if ts_type == "lambda":
        return "<lambda>"

    if ts_type == "import_statement":
        # Collect all dotted_name and aliased_import children
        parts = []
        for child in node.children:
            if child.node_type == "dotted_name":
                parts.append(_dotted_name(child))
            elif child.node_type == "aliased_import":
                parts.append(_aliased_import_name(child))
        return ", ".join(parts) if parts else None

    if ts_type == "import_from_statement":
        module_part = None
        imported_names: List[str] = []
        for child in node.children:
            if child.node_type == "relative_import":
                module_part = _relative_import_name(child)
            elif child.node_type == "dotted_name" and module_part is None:
                module_part = _dotted_name(child)
            elif child.node_type in ("dotted_name",):
                imported_names.append(_dotted_name(child))
            elif child.node_type == "aliased_import":
                imported_names.append(_aliased_import_name(child))
            elif child.node_type == "wildcard_import":
                imported_names.append("*")
        if module_part and imported_names:
            return f"from {module_part} import {', '.join(imported_names)}"
        elif module_part:
            return f"from {module_part} import ..."
        return None

    if ts_type == "assignment":
        # Left-hand side identifier or first identifier
        lhs = node.children[0] if node.children else None
        if lhs and lhs.node_type in ("identifier", "pattern_list", "tuple_pattern"):
            if lhs.node_type == "identifier":
                return lhs.text
            parts = [c.text for c in lhs.children if c.node_type == "identifier" and c.text]
            return ", ".join(parts) if parts else None
        return None

    if ts_type == "call":
        # Function being called — first child
        callee = node.children[0] if node.children else None
        if callee:
            if callee.node_type == "identifier":
                return callee.text
            if callee.node_type == "attribute":
                return _attribute_name(callee)
        return None

    if ts_type == "attribute":
        return _attribute_name(node)

    if ts_type == "identifier":
        return node.text

    return None


def _dotted_name(node: ParseTreeNode) -> str:
    """Join identifier children of a dotted_name node."""
    parts = [c.text for c in node.children if c.node_type == "identifier" and c.text]
    return ".".join(parts)


def _aliased_import_name(node: ParseTreeNode) -> str:
    """Return 'name as alias' for an aliased_import node."""
    parts = []
    for child in node.children:
        if child.node_type in ("dotted_name", "identifier") and child.text:
            if child.node_type == "dotted_name":
                parts.append(_dotted_name(child))
            else:
                parts.append(child.text)
    return " as ".join(parts)


def _attribute_name(node: ParseTreeNode) -> str:
    """Flatten an attribute chain: obj.attr.subattr."""
    parts = []
    for child in node.children:
        if child.node_type == "identifier" and child.text:
            parts.append(child.text)
        elif child.node_type == "attribute":
            parts.append(_attribute_name(child))
    return ".".join(parts)


# ---------------------------------------------------------------------------
# Type annotation extraction
# ---------------------------------------------------------------------------

def _extract_return_type(node: ParseTreeNode, source_bytes: bytes) -> Optional[str]:
    """Extract return type annotation from a function_definition node."""
    for child in node.children:
        if child.node_type == "type":
            return _node_slice(child, source_bytes).strip()
    return None


def _type_text(type_node: ParseTreeNode) -> str:
    """Flatten a type annotation node into a string representation."""
    if type_node.text is not None:
        return type_node.text
    # Recurse into children to build a string
    parts: List[str] = []
    for child in type_node.children:
        if child.node_type not in _SKIP_ANONYMOUS and child.text is not None:
            parts.append(child.text)
        elif child.node_type == "type":
            parts.append(_type_text(child))
        elif child.node_type == "identifier" and child.text:
            parts.append(child.text)
        elif child.node_type == "dotted_name":
            parts.append(_dotted_name(child))
    return "".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Decorator extraction
# ---------------------------------------------------------------------------

def _extract_decorators(node: ParseTreeNode, source_bytes: bytes) -> List[str]:
    """
    Extract decorator strings from a decorated_definition node.

    Each ``decorator`` child contributes one string entry, e.g. ``"@staticmethod"``.
    """
    decorators: List[str] = []
    for child in node.children:
        if child.node_type == "decorator":
            dec_str = _node_slice(child, source_bytes).strip()
            if dec_str:
                decorators.append(dec_str)
    return decorators


# ---------------------------------------------------------------------------
# Modifier extraction
# ---------------------------------------------------------------------------

def _extract_modifiers(node: ParseTreeNode, ts_type: str) -> List[str]:
    """Return modifier strings (e.g. 'async') from a definition node."""
    modifiers: List[str] = []
    if ts_type in ("function_definition",):
        # Check if preceded by 'async' keyword at parent level — handled via
        # the 'decorated_definition' wrapper or direct 'async' sibling detection.
        for child in node.children:
            if child.node_type == "async" or (not child.is_named and child.text == "async"):
                modifiers.append("async")
                break
    return modifiers


def _is_async_function(node: ParseTreeNode) -> bool:
    """Return True if the function_definition node has an async modifier."""
    for child in node.children:
        if not child.is_named and child.text == "async":
            return True
        if child.node_type == "async":
            return True
    return False


# ---------------------------------------------------------------------------
# Docstring extraction
# ---------------------------------------------------------------------------

def _node_slice(node: ParseTreeNode, source_bytes: bytes) -> str:
    """Extract raw text slice for a ParseTreeNode from source_bytes."""
    if node.text is not None:
        return node.text
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_docstring(block_node: Optional[ParseTreeNode], source_bytes: bytes) -> Optional[str]:
    """
    Extract the docstring from a block node (first statement if it's a string literal).

    Returns the stripped string content without enclosing quotes, or None.
    """
    if block_node is None or block_node.node_type != "block":
        return None

    for child in block_node.children:
        if child.node_type == "expression_statement" and child.children:
            first = child.children[0]
            if first.node_type in ("string", "concatenated_string"):
                raw = _node_slice(first, source_bytes)
                if raw:
                    # Strip quotes: ''', """, ', "
                    stripped = raw.strip()
                    for q in ('"""', "'''", '"', "'"):
                        if stripped.startswith(q) and stripped.endswith(q) and len(stripped) >= 2 * len(q):
                            return stripped[len(q):-len(q)].strip()
                    return stripped
        # First named child that is not a string → no docstring
        if child.is_named and child.node_type != "comment":
            break
    return None


# ---------------------------------------------------------------------------
# Range construction helpers
# ---------------------------------------------------------------------------

def _make_range(node: ParseTreeNode) -> NodeRange:
    """Build a ``NodeRange`` from a ``ParseTreeNode`` location data."""
    start_row, start_col = node.start_point
    end_row, end_col = node.end_point
    # tree-sitter is 0-indexed rows; DevBrain uses 1-indexed lines
    return NodeRange(
        start=NodeLocation(line=max(1, start_row + 1), column=start_col),
        end=NodeLocation(line=max(1, end_row + 1), column=max(0, end_col)),
        start_byte=node.start_byte,
        end_byte=node.end_byte,
    )


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------

class PythonASTConverter:
    """
    Converts a ``ParseTree`` produced by ``TreeSitterEngine`` into a DevBrain
    ``ASTRoot`` containing a semantically enriched ``ASTNode`` hierarchy.

    Usage::

        converter = PythonASTConverter()
        ast_root = converter.convert(parse_tree, source_bytes)
    """

    def __init__(self, max_depth: int = 200) -> None:
        """
        Parameters
        ----------
        max_depth:
            Maximum recursion depth for tree walking. Prevents stack overflow
            on deeply nested or pathological input.
        """
        self._max_depth = max_depth
        self._node_count = 0
        self._error_count = 0

    def convert(
        self,
        parse_tree: ParseTree,
        source_bytes: bytes,
    ) -> ASTRoot:
        """
        Convert a ``ParseTree`` into a ``ASTRoot``.

        Parameters
        ----------
        parse_tree:
            Output of ``TreeSitterEngine.parse()``.
        source_bytes:
            Original source bytes (used for docstring / literal text extraction).

        Returns
        -------
        ASTRoot
            Fully populated DevBrain AST.
        """
        self._node_count = 0
        self._error_count = 0

        root_ast_node = self._convert_node(
            ts_node=parse_tree.root_node,
            parent_id=None,
            depth=0,
            source_bytes=source_bytes,
        )

        ast_root = ASTRoot(
            file_path=parse_tree.file_path,
            language="python",
            root_node=root_ast_node,
        )
        ast_root.recalculate_metrics()
        return ast_root

    @property
    def node_count(self) -> int:
        """Total AST nodes emitted during last ``convert()`` call."""
        return self._node_count

    @property
    def error_count(self) -> int:
        """Count of ERROR / MISSING nodes encountered during last ``convert()`` call."""
        return self._error_count

    # ------------------------------------------------------------------
    # Core recursive converter
    # ------------------------------------------------------------------

    def _convert_node(
        self,
        ts_node: ParseTreeNode,
        parent_id: Optional[str],
        depth: int,
        source_bytes: bytes,
    ) -> ASTNode:
        """
        Recursively convert a ``ParseTreeNode`` into an ``ASTNode``.

        The conversion strategy:

        1. Determine ``NodeType`` from ``_NODE_TYPE_MAP`` (or UNKNOWN).
        2. For named constructs, extract name, type annotation, modifiers,
           decorators, and docstring.
        3. Recursively convert named children, skipping anonymous punctuation.
        4. For ``decorated_definition``, promote inner function/class metadata
           up to the parent node.
        5. Build parent-child relationship links.
        """
        if ts_node.is_error or ts_node.is_missing:
            self._error_count += 1

        ts_type = ts_node.node_type
        node_type = _NODE_TYPE_MAP.get(ts_type, NodeType.STATEMENT if ts_node.is_named else NodeType.UNKNOWN)

        # Build metadata
        metadata = NodeMetadata()
        name: Optional[str] = None
        value: Optional[str] = None

        # --- Special per-type enrichment ---
        if ts_type in (
            "import_statement",
            "import_from_statement",
            "function_definition",
            "class_definition",
            "lambda",
            "assignment",
            "call",
            "attribute",
            "identifier",
        ):
            if ts_type in ("import_statement", "import_from_statement"):
                name = _node_slice(ts_node, source_bytes).strip()
            else:
                name = _extract_name(ts_node, ts_type)

        # Async modifier detection
        if ts_type == "function_definition" and _is_async_function(ts_node):
            metadata.modifiers.append("async")
            node_type = NodeType.FUNCTION

        # Decorated definition: resolve inner type + collect decorators
        if ts_type == "decorated_definition":
            decorators = _extract_decorators(ts_node, source_bytes)
            inner_child = None
            for child in ts_node.children:
                if child.node_type in ("function_definition", "class_definition", "async_function_definition"):
                    inner_child = child
                    break
            if inner_child:
                inner_ast = self._convert_node(inner_child, parent_id, depth, source_bytes)
                inner_ast.metadata.decorators = decorators + inner_ast.metadata.decorators
                inner_ast.range = _make_range(ts_node)
                return inner_ast

        # Parameter nodes
        if ts_type in ("parameter", "typed_parameter", "default_parameter", "typed_default_parameter", "list_splat_pattern", "dictionary_splat_pattern"):
            node_type = NodeType.PARAMETER
            name = _extract_name(ts_node, ts_type)
            type_child = _first_named_child(ts_node, "type")
            if type_child:
                metadata.type_annotation = _node_slice(type_child, source_bytes).strip()
            for child in ts_node.children:
                if child.is_named and child.node_type not in ("identifier", "type"):
                    value = _node_slice(child, source_bytes)
                    break

        # Yield marker
        if ts_type in ("yield", "yield_statement"):
            node_type = NodeType.STATEMENT
            value = "yield"

        # Return type annotation for functions
        if ts_type in ("function_definition", "async_function_definition"):
            ret_type = _extract_return_type(ts_node, source_bytes)
            if ret_type:
                metadata.type_annotation = ret_type
            metadata.is_definition = True

        if ts_type == "class_definition":
            metadata.is_definition = True
            base_classes = []
            arg_list = _first_named_child(ts_node, "argument_list")
            if arg_list:
                for child in arg_list.children:
                    if child.is_named:
                        bname = _node_slice(child, source_bytes)
                        if bname:
                            base_classes.append(bname)
            metadata.custom["base_classes"] = base_classes

        # Imports
        if ts_type in ("import_statement", "import_from_statement", "future_import_statement"):
            metadata.is_reference = True

        # Assignment
        if ts_type == "assignment":
            metadata.is_definition = True

        # Docstring extraction — look at block child
        if ts_type in ("function_definition", "class_definition", "async_function_definition"):
            block = _first_named_child(ts_node, "block")
            docstring = _extract_docstring(block, source_bytes)
            if docstring:
                metadata.docstring = docstring

        # Module docstring
        if ts_type == "module":
            node_type = NodeType.MODULE
            metadata.is_definition = True
            # Module docstring: first expression_statement containing a string
            for child in ts_node.children:
                if child.node_type == "expression_statement" and child.children:
                    first = child.children[0]
                    if first.node_type in ("string", "concatenated_string"):
                        raw = _node_slice(first, source_bytes)
                        stripped = raw.strip()
                        for q in ('"""', "'''", '"', "'"):
                            if stripped.startswith(q) and stripped.endswith(q) and len(stripped) >= 2 * len(q):
                                metadata.docstring = stripped[len(q):-len(q)].strip()
                                break
                        else:
                            metadata.docstring = stripped
                    break

        # Literal value
        if ts_type in ("string", "integer", "float", "true", "false", "none"):
            value = ts_node.text

        # Comment text
        if ts_type == "comment":
            value = ts_node.text

        # Build the ASTNode
        node_range = _make_range(ts_node)
        ast_node = ASTNode(
            type=node_type,
            name=name,
            value=value,
            range=node_range,
            metadata=metadata,
        )

        if parent_id is not None:
            ast_node.relationships.parent_id = parent_id

        self._node_count += 1

        # --- Recurse into children ---
        if depth < self._max_depth:
            children_to_convert = self._select_children(ts_node, ts_type, depth)
            for child_ts_node in children_to_convert:
                child_ast = self._convert_node(
                    ts_node=child_ts_node,
                    parent_id=ast_node.node_id,
                    depth=depth + 1,
                    source_bytes=source_bytes,
                )
                ast_node.add_child(child_ast)
        else:
            logger.debug(
                f"[PythonASTConverter] Max depth {self._max_depth} reached at "
                f"'{ts_node.node_type}' — children truncated."
            )

        return ast_node

    def _select_children(
        self,
        ts_node: ParseTreeNode,
        ts_type: str,
        depth: int,
    ) -> List[ParseTreeNode]:
        """
        Choose which children of ``ts_node`` to recurse into.

        Rules:
        - Named children are always included.
        - Anonymous tokens that are in ``_SKIP_ANONYMOUS`` are excluded.
        - For ``parameters`` nodes, we include all named parameter children.
        - For ``block`` nodes, we include all named statement children.
        """
        result: List[ParseTreeNode] = []
        for child in ts_node.children:
            if not child.is_named:
                # Skip common anonymous punctuation / keywords
                if child.text in _SKIP_ANONYMOUS or child.node_type in _SKIP_ANONYMOUS:
                    continue
                # Keep anonymous nodes that carry meaningful content (e.g. operators visible in text)
                if child.node_type in ("*", "**", "//", "->", ":", "=", "!=", "==", "<", ">", "<=", ">="):
                    result.append(child)
                continue
            result.append(child)
        return result
