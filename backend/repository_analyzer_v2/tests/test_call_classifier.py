"""
tests/test_call_classifier.py
------------------------------
Unit tests for CallClassifier — verifying classification across all 10 call types.
"""

from models.call_models import CallType
from models.symbol import Symbol, SymbolKind
from analysis.function_call_detection.call_classifier import CallClassifier


class TestCallClassifier:
    def setup_method(self):
        self.classifier = CallClassifier()

    def test_direct_function_call(self):
        res = self.classifier.classify("login")
        assert res.call_type == CallType.FUNCTION
        assert not res.is_method
        assert not res.is_constructor

    def test_method_call(self):
        res = self.classifier.classify("user.login")
        assert res.call_type == CallType.METHOD
        assert res.is_method

    def test_async_call(self):
        res = self.classifier.classify("service.run", is_async=True)
        assert res.call_type == CallType.ASYNC
        assert res.is_async

    def test_constructor_call_by_name(self):
        res = self.classifier.classify("User")
        assert res.call_type == CallType.CONSTRUCTOR
        assert res.is_constructor

        res_fastapi = self.classifier.classify("FastAPI")
        assert res_fastapi.call_type == CallType.CONSTRUCTOR
        assert res_fastapi.is_constructor

    def test_constructor_call_by_class_symbol(self):
        sym = Symbol(
            id="sym-123",
            fqn="app.models.User",
            name="User",
            kind=SymbolKind.CLASS,
            file_path="app/models.py",
        )
        res = self.classifier.classify("User", callee_symbol=sym)
        assert res.call_type == CallType.CONSTRUCTOR
        assert res.is_constructor

    def test_class_method_call(self):
        res = self.classifier.classify("User.build")
        assert res.call_type == CallType.CLASS_METHOD
        assert res.is_classmethod
        assert res.is_method

    def test_super_call(self):
        res = self.classifier.classify("super().__init__")
        assert res.call_type == CallType.SUPER
        assert res.is_super_call

        res_save = self.classifier.classify("super().save")
        assert res_save.call_type == CallType.SUPER
        assert res_save.is_super_call

    def test_lambda_call(self):
        res = self.classifier.classify("<lambda>")
        assert res.call_type == CallType.LAMBDA
        assert res.is_lambda

    def test_classmethod_decorator(self):
        sym = Symbol(
            id="sym-cm",
            fqn="User.create",
            name="create",
            kind=SymbolKind.METHOD,
            file_path="user.py",
            metadata={"method_modifiers": ["classmethod"]},
        )
        res = self.classifier.classify("User.create", callee_symbol=sym)
        assert res.call_type == CallType.CLASS_METHOD
        assert res.is_classmethod

    def test_staticmethod_decorator(self):
        sym = Symbol(
            id="sym-sm",
            fqn="Math.add",
            name="add",
            kind=SymbolKind.METHOD,
            file_path="math.py",
            metadata={"method_modifiers": ["staticmethod"]},
        )
        res = self.classifier.classify("Math.add", callee_symbol=sym)
        assert res.call_type == CallType.STATIC_METHOD
        assert res.is_staticmethod
