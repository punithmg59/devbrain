"""
tests/test_module_index.py
---------------------------
Unit tests for ModuleIndex file-path/FQN mapping and relative import resolution.
"""

from analysis.import_resolution.module_index import ModuleIndex


class TestModuleIndex:
    def test_path_to_fqn_conversion(self):
        assert ModuleIndex.path_to_fqn("app/services/user.py") == "app.services.user"
        assert ModuleIndex.path_to_fqn("app/auth/__init__.py") == "app.auth"
        assert ModuleIndex.path_to_fqn("core/engine/parser.py") == "core.engine.parser"

    def test_bidirectional_registration_and_lookup(self):
        index = ModuleIndex()
        fqn = index.register_file("app/services/user.py")

        assert fqn == "app.services.user"
        assert index.get_file_path("app.services.user") == "app/services/user.py"
        assert index.get_module_fqn("app/services/user.py") == "app.services.user"
        assert index.is_registered_module("app.services.user") is True

    def test_standard_library_detection(self):
        assert ModuleIndex.is_stdlib_module("os") is True
        assert ModuleIndex.is_stdlib_module("sys") is True
        assert ModuleIndex.is_stdlib_module("json") is True
        assert ModuleIndex.is_stdlib_module("asyncio") is True
        assert ModuleIndex.is_stdlib_module("urllib.parse") is True

        assert ModuleIndex.is_stdlib_module("requests") is False
        assert ModuleIndex.is_stdlib_module("fastapi") is False
        assert ModuleIndex.is_stdlib_module("app.auth") is False

    def test_relative_import_resolution(self):
        index = ModuleIndex()

        # from .user import User (in app.auth.service) -> app.auth.user
        target1 = index.resolve_relative_import("app.auth.service", relative_level=1, imported_module_part="user")
        assert target1 == "app.auth.user"

        # from ..database import DB (in app.auth.service) -> app.database
        target2 = index.resolve_relative_import("app.auth.service", relative_level=2, imported_module_part="database")
        assert target2 == "app.database"

        # level higher than depth
        target3 = index.resolve_relative_import("app.auth", relative_level=5, imported_module_part="something")
        assert target3 is None
