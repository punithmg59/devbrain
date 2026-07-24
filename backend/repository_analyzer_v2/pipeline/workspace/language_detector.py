"""
pipeline/workspace/language_detector.py
----------------------------------------
Step 1 — Language & Technology Detector Subsystem.

Identifies programming languages and project/framework metadata using file extension
distribution and manifest file signatures without executing or parsing AST code.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Set, Tuple

from models.repository import RepositoryFile
from pipeline.workspace.models import DetectedFramework, DetectedLanguage
from utils.logger import get_logger

logger = get_logger(__name__)

# Primary language extension lookup map
EXTENSION_TO_LANGUAGE: Dict[str, Tuple[str, str]] = {
    # Initial supported languages
    "py": ("python", "py"),
    "pyi": ("python", "pyi"),
    "ts": ("typescript", "ts"),
    "tsx": ("typescript", "tsx"),
    "js": ("javascript", "js"),
    "jsx": ("javascript", "jsx"),
    "mjs": ("javascript", "mjs"),
    "cjs": ("javascript", "cjs"),

    # Future-ready language extensibility map
    "java": ("java", "java"),
    "go": ("go", "go"),
    "rs": ("rust", "rs"),
    "cs": ("csharp", "cs"),
    "cpp": ("cpp", "cpp"),
    "cxx": ("cpp", "cpp"),
    "cc": ("cpp", "cc"),
    "c": ("c", "c"),
    "h": ("c", "h"),
    "hpp": ("cpp", "hpp"),
    "kt": ("kotlin", "kt"),
    "kts": ("kotlin", "kts"),
    "swift": ("swift", "swift"),
    "php": ("php", "php"),
    "rb": ("ruby", "rb"),
}


class LanguageDetector:
    """
    Detector engine for languages and framework project manifests.

    Usage::

        detector = LanguageDetector()
        languages, frameworks = detector.detect_technologies(repo_root, analyzable_files)
    """

    def detect_technologies(
        self,
        repository_root: str,
        files: List[RepositoryFile],
    ) -> Tuple[List[DetectedLanguage], List[DetectedFramework]]:
        """
        Identify active programming languages and framework manifests.

        Parameters
        ----------
        repository_root:
            Absolute filesystem path of repository.
        files:
            List of `RepositoryFile` objects.

        Returns
        -------
        Tuple of (List[DetectedLanguage], List[DetectedFramework])
        """
        lang_stats: Dict[str, Dict[str, Any]] = {}
        frameworks: List[DetectedFramework] = []
        framework_names_seen: Set[str] = set()

        # 1. Classify Files by Extension and Set RepositoryFile.language
        for f in files:
            ext = f.extension.lower()
            if ext in EXTENSION_TO_LANGUAGE:
                lang_name, primary_ext = EXTENSION_TO_LANGUAGE[ext]
                f.language = lang_name

                if lang_name not in lang_stats:
                    lang_stats[lang_name] = {
                        "primary_ext": primary_ext,
                        "file_count": 0,
                        "line_count": 0,
                    }
                lang_stats[lang_name]["file_count"] += 1
                lang_stats[lang_name]["line_count"] += f.line_count
            else:
                f.language = "unknown"

        # 2. Build DetectedLanguage objects
        detected_languages: List[DetectedLanguage] = []
        total_files = max(1, len(files))

        for lang_name, stats in lang_stats.items():
            conf = round(min(1.0, stats["file_count"] / float(total_files) + 0.5), 2)
            detected_languages.append(
                DetectedLanguage(
                    name=lang_name,
                    primary_extension=stats["primary_ext"],
                    confidence=conf,
                    file_count=stats["file_count"],
                    line_count=stats["line_count"],
                )
            )

        # Sort languages by file count descending
        detected_languages.sort(key=lambda l: l.file_count, reverse=True)

        # 3. Detect Project Frameworks via Manifests
        manifest_files = [
            "package.json", "tsconfig.json", "pyproject.toml", "requirements.txt",
            "Pipfile", "setup.py", "pom.xml", "build.gradle", "go.mod", "Cargo.toml"
        ]

        for root, _, filenames in os.walk(repository_root):
            if ".git" in root or "node_modules" in root or "__pycache__" in root:
                continue
            for fname in filenames:
                if fname in manifest_files:
                    abs_manifest = os.path.join(root, fname)
                    rel_manifest = os.path.relpath(abs_manifest, repository_root).replace("\\", "/")
                    detected_fw = self._analyze_manifest(fname, abs_manifest, rel_manifest)
                    for fw in detected_fw:
                        if fw.name not in framework_names_seen:
                            framework_names_seen.add(fw.name)
                            frameworks.append(fw)

        logger.debug(
            f"[LanguageDetector] Identified {len(detected_languages)} languages, "
            f"{len(frameworks)} frameworks in '{repository_root}'"
        )

        return detected_languages, frameworks

    def _analyze_manifest(
        self,
        manifest_name: str,
        abs_path: str,
        rel_path: str,
    ) -> List[DetectedFramework]:
        """Inspect project manifest headers for framework signatures."""
        detected: List[DetectedFramework] = []

        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if manifest_name == "package.json":
                try:
                    data = json.loads(content)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    if "next" in deps:
                        detected.append(DetectedFramework(name="Next.js", manifest_file=rel_path, version=deps["next"]))
                    if "react" in deps:
                        detected.append(DetectedFramework(name="React", manifest_file=rel_path, version=deps["react"]))
                    if "express" in deps:
                        detected.append(DetectedFramework(name="Express", manifest_file=rel_path, version=deps["express"]))
                    if "vue" in deps:
                        detected.append(DetectedFramework(name="Vue", manifest_file=rel_path, version=deps["vue"]))
                    if "svelte" in deps:
                        detected.append(DetectedFramework(name="Svelte", manifest_file=rel_path, version=deps["svelte"]))
                    if "@nestjs/core" in deps:
                        detected.append(DetectedFramework(name="NestJS", manifest_file=rel_path, version=deps["@nestjs/core"]))
                except Exception:
                    pass
                detected.append(DetectedFramework(name="Node.js", manifest_file=rel_path))

            elif manifest_name == "tsconfig.json":
                detected.append(DetectedFramework(name="TypeScript Project", manifest_file=rel_path))

            elif manifest_name in ("pyproject.toml", "requirements.txt", "Pipfile", "setup.py"):
                content_lower = content.lower()
                if "fastapi" in content_lower:
                    detected.append(DetectedFramework(name="FastAPI", manifest_file=rel_path))
                if "django" in content_lower:
                    detected.append(DetectedFramework(name="Django", manifest_file=rel_path))
                if "flask" in content_lower:
                    detected.append(DetectedFramework(name="Flask", manifest_file=rel_path))
                if "pytest" in content_lower:
                    detected.append(DetectedFramework(name="Pytest", manifest_file=rel_path))

            elif manifest_name == "Cargo.toml":
                detected.append(DetectedFramework(name="Cargo / Rust Package", manifest_file=rel_path))

            elif manifest_name == "go.mod":
                detected.append(DetectedFramework(name="Go Module", manifest_file=rel_path))

            elif manifest_name == "pom.xml":
                detected.append(DetectedFramework(name="Maven Project", manifest_file=rel_path))

            elif manifest_name == "build.gradle":
                detected.append(DetectedFramework(name="Gradle Project", manifest_file=rel_path))

        except Exception as exc:
            logger.warning(f"[LanguageDetector] Error reading manifest '{rel_path}': {exc}")

        return detected
