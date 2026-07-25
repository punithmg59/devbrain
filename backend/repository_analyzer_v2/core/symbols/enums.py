"""
core/symbols/enums.py
---------------------
Canonical Enums for the Language-Independent Symbol Model.
"""

from enum import Enum


class Language(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CSHARP = "csharp"
    KOTLIN = "kotlin"
    SWIFT = "swift"
    SCALA = "scala"
    CPP = "cpp"
    C = "c"
    PHP = "php"
    RUBY = "ruby"
    FUTURE = "future"


class SymbolKind(str, Enum):
    """Canonical classification of declared symbol entities across programming languages."""
    MODULE = "module"
    PACKAGE = "package"
    NAMESPACE = "namespace"
    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    TRAIT = "trait"
    PROTOCOL = "protocol"
    RECORD = "record"
    UNION = "union"
    FUNCTION = "function"
    METHOD = "method"
    CONSTRUCTOR = "constructor"
    DESTRUCTOR = "destructor"
    PROPERTY = "property"
    FIELD = "field"
    VARIABLE = "variable"
    CONSTANT = "constant"
    PARAMETER = "parameter"
    TYPE_ALIAS = "type_alias"
    GENERIC_PARAMETER = "generic_parameter"
    DECORATOR = "decorator"
    ANNOTATION = "annotation"
    MACRO = "macro"
    IMPORT = "import"
    EXPORT = "export"
    UNKNOWN = "unknown"


class VisibilityKind(str, Enum):
    """Access visibility modifier classification."""
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"
    INTERNAL = "internal"
    PACKAGE = "package"
    FILE = "file"
    LOCAL = "local"
    UNKNOWN = "unknown"


class AccessibilityKind(str, Enum):
    """Access read/write/execution permissions classification."""
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    READ_WRITE = "read_write"
    EXECUTE = "execute"
    PRIVATE_ACCESS = "private_access"
    UNRESTRICTED = "unrestricted"
    UNKNOWN = "unknown"


class ModifierKind(str, Enum):
    """Language-independent modifiers."""
    STATIC = "static"
    ABSTRACT = "abstract"
    VIRTUAL = "virtual"
    OVERRIDE = "override"
    ASYNC = "async"
    CONST = "const"
    READONLY = "readonly"
    FINAL = "final"
    SEALED = "sealed"
    PARTIAL = "partial"
    EXTENSION = "extension"
    UNSAFE = "unsafe"
    SYNCHRONIZED = "synchronized"
    NATIVE = "native"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    MUTABLE = "mutable"
    INLINE = "inline"
    EXTERN = "extern"
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"


class RelationshipKind(str, Enum):
    """Metadata-only classification of relationships between symbols."""
    DEFINES = "defines"
    CALLS = "calls"
    IMPORTS = "imports"
    USES = "uses"
    OVERRIDES = "overrides"
    IMPLEMENTS = "implements"
    INHERITS = "inherits"
    CREATES = "creates"
    THROWS = "throws"
    RETURNS = "returns"
    REFERENCES = "references"


class DocumentationFormat(str, Enum):
    """Format of documentation strings."""
    MARKDOWN = "markdown"
    JSDOC = "jsdoc"
    JAVADOC = "javadoc"
    DOXYGEN = "doxygen"
    RUSTDOC = "rustdoc"
    PLAIN = "plain"


class OriginKind(str, Enum):
    """Origin source of a symbol declaration."""
    SOURCE = "source"
    SYNTHESIZED = "synthesized"
    STDLIB = "stdlib"
    THIRD_PARTY = "third_party"
    GENERATED = "generated"


class VarianceKind(str, Enum):
    """Generic parameter type variance."""
    INVARIANT = "invariant"
    COVARIANT = "covariant"
    CONTRAVARIANT = "contravariant"
