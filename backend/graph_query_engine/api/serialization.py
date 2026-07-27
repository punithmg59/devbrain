"""
Public Query API Serialization.

JSON, YAML, and Binary serializers for Public Query API requests and responses.
"""

from abc import ABC, abstractmethod
import json
from typing import Any, Dict, Union

from graph_query_engine.api.request import QueryRequest
from graph_query_engine.api.response import QueryResponse


class QuerySerializer(ABC):
    """Abstract base class for Query API serializers."""

    @abstractmethod
    def serialize_request(self, request: QueryRequest) -> Union[str, bytes]:
        """Serializes QueryRequest into formatted string or bytes."""
        pass

    @abstractmethod
    def deserialize_request(self, payload: Union[str, bytes]) -> QueryRequest:
        """Deserializes QueryRequest from formatted payload."""
        pass

    @abstractmethod
    def serialize_response(self, response: QueryResponse) -> Union[str, bytes]:
        """Serializes QueryResponse into formatted string or bytes."""
        pass

    @abstractmethod
    def deserialize_response(self, payload: Union[str, bytes]) -> QueryResponse:
        """Deserializes QueryResponse from formatted payload."""
        pass


class JSONQuerySerializer(QuerySerializer):
    """JSON serializer for Public Query API models."""

    def serialize_request(self, request: QueryRequest) -> str:
        return request.model_dump_json(indent=2)

    def deserialize_request(self, payload: Union[str, bytes]) -> QueryRequest:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        return QueryRequest.model_validate_json(text)

    def serialize_response(self, response: QueryResponse) -> str:
        return response.model_dump_json(indent=2)

    def deserialize_response(self, payload: Union[str, bytes]) -> QueryResponse:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        return QueryResponse.model_validate_json(text)


class YAMLQuerySerializer(QuerySerializer):
    """YAML serializer placeholder using JSON fallback if PyYAML is unavailable."""

    def serialize_request(self, request: QueryRequest) -> str:
        try:
            import yaml
            return yaml.dump(request.model_dump(mode="json"), sort_keys=False)
        except ImportError:
            return json.dumps(request.model_dump(mode="json"), indent=2)

    def deserialize_request(self, payload: Union[str, bytes]) -> QueryRequest:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        try:
            import yaml
            data = yaml.safe_load(text)
        except ImportError:
            data = json.loads(text)
        return QueryRequest.model_validate(data)

    def serialize_response(self, response: QueryResponse) -> str:
        try:
            import yaml
            return yaml.dump(response.model_dump(mode="json"), sort_keys=False)
        except ImportError:
            return json.dumps(response.model_dump(mode="json"), indent=2)

    def deserialize_response(self, payload: Union[str, bytes]) -> QueryResponse:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        try:
            import yaml
            data = yaml.safe_load(text)
        except ImportError:
            data = json.loads(text)
        return QueryResponse.model_validate(data)


class BinaryQuerySerializer(QuerySerializer):
    """Binary UTF-8 bytes serializer."""

    def __init__(self) -> None:
        self._json_serializer = JSONQuerySerializer()

    def serialize_request(self, request: QueryRequest) -> bytes:
        return self._json_serializer.serialize_request(request).encode("utf-8")

    def deserialize_request(self, payload: Union[str, bytes]) -> QueryRequest:
        raw_bytes = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        return self._json_serializer.deserialize_request(raw_bytes.decode("utf-8"))

    def serialize_response(self, response: QueryResponse) -> bytes:
        return self._json_serializer.serialize_response(response).encode("utf-8")

    def deserialize_response(self, payload: Union[str, bytes]) -> QueryResponse:
        raw_bytes = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        return self._json_serializer.deserialize_response(raw_bytes.decode("utf-8"))


__all__ = [
    "QuerySerializer",
    "JSONQuerySerializer",
    "YAMLQuerySerializer",
    "BinaryQuerySerializer",
]
