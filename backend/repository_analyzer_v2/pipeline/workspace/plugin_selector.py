"""
pipeline/workspace/plugin_selector.py
--------------------------------------
Step 1 — Builder Plugin Selector Subsystem.

Maps detected languages and frameworks to required DevBrain Builder Plugin requirement specs
without instantiating or executing plugin logic.
"""

from __future__ import annotations

from typing import List, Set

from pipeline.workspace.models import DetectedFramework, DetectedLanguage, PluginRequirement
from utils.logger import get_logger

logger = get_logger(__name__)

# Known plugin specs catalog
LANGUAGE_PLUGIN_MAP = {
    "python": PluginRequirement(
        plugin_id="devbrain.plugin.python",
        target_language="python",
        priority=100,
        is_required=True,
    ),
    "typescript": PluginRequirement(
        plugin_id="devbrain.plugin.typescript",
        target_language="typescript",
        priority=100,
        is_required=True,
    ),
    "javascript": PluginRequirement(
        plugin_id="devbrain.plugin.javascript",
        target_language="javascript",
        priority=90,
        is_required=True,
    ),
}


class PluginSelector:
    """
    Selects required Builder Plugin specs for graph building based on detected technology stack.

    Usage::

        selector = PluginSelector()
        requirements = selector.select_plugins(languages, frameworks)
    """

    def select_plugins(
        self,
        languages: List[DetectedLanguage],
        frameworks: List[DetectedFramework],
    ) -> List[PluginRequirement]:
        """
        Determine required Builder Plugin requirement specifications.

        Parameters
        ----------
        languages:
            List of `DetectedLanguage` objects.
        frameworks:
            List of `DetectedFramework` objects.

        Returns
        -------
        List of PluginRequirement
        """
        requirements: List[PluginRequirement] = []
        selected_plugin_ids: Set[str] = set()

        # 1. Select Language Builder Plugins
        for lang in languages:
            lang_name = lang.name.lower()
            if lang_name in LANGUAGE_PLUGIN_MAP:
                req = LANGUAGE_PLUGIN_MAP[lang_name]
                if req.plugin_id not in selected_plugin_ids:
                    selected_plugin_ids.add(req.plugin_id)
                    requirements.append(req)

        # 2. Select Framework Extension Plugins if present
        for fw in frameworks:
            fw_name = fw.name.lower()
            if "fastapi" in fw_name:
                p_id = "devbrain.plugin.python.fastapi"
                if p_id not in selected_plugin_ids:
                    selected_plugin_ids.add(p_id)
                    requirements.append(
                        PluginRequirement(
                            plugin_id=p_id,
                            target_language="python",
                            framework="FastAPI",
                            priority=150,
                            is_required=False,
                        )
                    )
            elif "react" in fw_name or "next.js" in fw_name:
                p_id = "devbrain.plugin.typescript.react"
                if p_id not in selected_plugin_ids:
                    selected_plugin_ids.add(p_id)
                    requirements.append(
                        PluginRequirement(
                            plugin_id=p_id,
                            target_language="typescript",
                            framework=fw.name,
                            priority=150,
                            is_required=False,
                        )
                    )

        # Sort requirements by priority descending
        requirements.sort(key=lambda r: r.priority, reverse=True)

        logger.debug(f"[PluginSelector] Selected {len(requirements)} plugin requirements")
        return requirements
