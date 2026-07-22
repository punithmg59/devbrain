"""
utils/language_detector.py
---------------------------
Maps file paths and extensions to supported programming language Enums.
"""

import pathlib
from typing import Dict, Union

from models.repository import Language


class LanguageDetector:
    """Detects programming languages based on file extensions."""

    EXTENSION_MAP: Dict[str, Language] = {
        # Python
        "py": Language.PYTHON,
        "pyi": Language.PYTHON,
        "pyw": Language.PYTHON,
        # TypeScript
        "ts": Language.TYPESCRIPT,
        "tsx": Language.TYPESCRIPT,
        "mts": Language.TYPESCRIPT,
        "cts": Language.TYPESCRIPT,
        # JavaScript
        "js": Language.JAVASCRIPT,
        "jsx": Language.JAVASCRIPT,
        "mjs": Language.JAVASCRIPT,
        "cjs": Language.JAVASCRIPT,
        # Java
        "java": Language.JAVA,
        # Go
        "go": Language.GO,
        # C#
        "cs": Language.CSHARP,
    }

    @classmethod
    def detect(cls, path_or_ext: Union[str, pathlib.Path]) -> Language:
        """
        Detect language from file path or extension string.

        :param path_or_ext: File path or extension (with or without dot)
        :return: Language Enum
        """
        if isinstance(path_or_ext, pathlib.Path):
            ext = path_or_ext.suffix.lstrip(".").lower()
        else:
            p = pathlib.Path(path_or_ext)
            ext = p.suffix.lstrip(".").lower() if p.suffix else path_or_ext.lstrip(".").lower()

        return cls.EXTENSION_MAP.get(ext, Language.UNKNOWN)
