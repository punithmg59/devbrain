"""
Unit tests for Public Query API QuerySerializer implementations.
"""

from graph_query_engine.api.request import QueryRequest
from graph_query_engine.api.response import QueryResponse, ResponseStatus
from graph_query_engine.api.result import QueryResult
from graph_query_engine.api.serialization import (
    BinaryQuerySerializer,
    JSONQuerySerializer,
    YAMLQuerySerializer,
)


def test_json_serializer():
    serializer = JSONQuerySerializer()
    req = QueryRequest(operation="lookup_class", target="MyClass")

    text = serializer.serialize_request(req)
    req_deserialized = serializer.deserialize_request(text)

    assert req_deserialized.operation == req.operation
    assert req_deserialized.target == req.target

    res = QueryResponse(
        request_id=req.request_id,
        status=ResponseStatus.SUCCESS,
        result=QueryResult(target="MyClass", nodes=[{"id": "MyClass"}]),
    )

    res_text = serializer.serialize_response(res)
    res_deserialized = serializer.deserialize_response(res_text)

    assert res_deserialized.request_id == res.request_id
    assert res_deserialized.status == ResponseStatus.SUCCESS


def test_yaml_serializer():
    serializer = YAMLQuerySerializer()
    req = QueryRequest(operation="lookup_class", target="MyClass")

    text = serializer.serialize_request(req)
    req_deserialized = serializer.deserialize_request(text)

    assert req_deserialized.operation == req.operation
    assert req_deserialized.target == req.target


def test_binary_serializer():
    serializer = BinaryQuerySerializer()
    req = QueryRequest(operation="lookup_class", target="MyClass")

    raw_bytes = serializer.serialize_request(req)
    assert isinstance(raw_bytes, bytes)

    req_deserialized = serializer.deserialize_request(raw_bytes)
    assert req_deserialized.operation == req.operation
    assert req_deserialized.target == req.target
