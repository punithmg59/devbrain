"""
tests/test_call_index.py
-------------------------
Unit tests for CallIndex — O(1) multi-index lookups.
"""

from models.call_models import CallRecord, CallType
from analysis.function_call_detection.call_index import CallIndex


class TestCallIndex:
    def test_multi_index_lookups(self):
        c1 = CallRecord(
            call_id="call-1",
            caller_symbol_id="caller-sym-1",
            callee_symbol_id="callee-sym-1",
            callee_name="login",
            file_path="app/auth.py",
            line=5,
            column=4,
            call_type=CallType.FUNCTION,
        )
        c2 = CallRecord(
            call_id="call-2",
            caller_symbol_id="caller-sym-1",
            callee_symbol_id="callee-sym-2",
            callee_name="User",
            file_path="app/auth.py",
            line=10,
            column=4,
            call_type=CallType.CONSTRUCTOR,
            is_constructor=True,
        )
        c3 = CallRecord(
            call_id="call-3",
            caller_symbol_id="caller-sym-2",
            callee_symbol_id="callee-sym-1",
            callee_name="login",
            file_path="app/user.py",
            line=15,
            column=8,
            call_type=CallType.FUNCTION,
        )

        index = CallIndex()
        index.build([c1, c2, c3])

        assert len(index) == 3
        assert index.find_call("call-1") == c1

        caller1_calls = index.find_calls_by_caller("caller-sym-1")
        assert len(caller1_calls) == 2
        assert c1 in caller1_calls
        assert c2 in caller1_calls

        callee1_calls = index.find_calls_by_callee("callee-sym-1")
        assert len(callee1_calls) == 2
        assert c1 in callee1_calls
        assert c3 in callee1_calls

        auth_calls = index.find_calls_in_file("app/auth.py")
        assert len(auth_calls) == 2

        constructors = index.find_constructor_calls()
        assert len(constructors) == 1
        assert constructors[0] == c2

        func_calls = index.find_calls_by_type(CallType.FUNCTION)
        assert len(func_calls) == 2
