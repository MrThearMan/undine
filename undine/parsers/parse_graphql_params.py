from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.http.request import MediaType

from undine import error_codes
from undine.errors import GraphQLStatusError
from undine.http.files import place_files
from undine.typing import GraphQLParams

if TYPE_CHECKING:
    from django.core.files import File
    from django.http import HttpRequest


class GraphQLRequestParamsParser:
    """Parse GraphQLParams from a given HttpRequest."""

    @classmethod
    def run(cls, request: HttpRequest) -> GraphQLParams:
        data = cls.parse_body(request)
        return cls.get_graphql_params(data)

    @classmethod
    def parse_body(cls, request: HttpRequest) -> dict[str, str]:
        if request.method == "GET":
            return request.GET.dict()

        if not request.content_type:
            msg = "Must provide a 'Content-Type' header."
            raise GraphQLStatusError(msg, status=415, code=error_codes.CONTENT_TYPE_MISSING)

        content_type = MediaType(request.content_type)
        charset: str = content_type.params.get("charset", "utf-8")

        if content_type.main_type == "application":
            if content_type.sub_type == "json":
                return cls.parse_json_body(request.body, charset=charset)
            if content_type.sub_type == "graphql":
                return {"query": cls.decode_body(request.body, charset=charset)}
            if content_type.sub_type == "x-www-form-urlencoded":
                return request.POST.dict()

        if content_type.main_type == "multipart" and content_type.sub_type == "form-data":
            if request.FILES:
                return cls.parse_file_uploads(request.POST.dict(), request.FILES.dict())
            return request.POST.dict()

        msg = f"'{content_type}' is not a supported content type."
        raise GraphQLStatusError(msg, status=415, code=error_codes.UNSUPPORTED_CONTENT_TYPE)

    @classmethod
    def decode_body(cls, body: bytes, charset: str = "utf-8") -> str:
        try:
            return body.decode(encoding=charset)
        except Exception as error:
            msg = f"Could not decode body with encoding '{charset}'."
            raise GraphQLStatusError(msg, status=400, code=error_codes.DECODING_ERROR) from error

    @classmethod
    def load_json_dict(cls, string: str, *, decode_error_msg: str, type_error_msg: str) -> dict[str, Any]:
        try:
            data = json.loads(string)
        except Exception as error:
            raise GraphQLStatusError(decode_error_msg, status=400, code=error_codes.DECODING_ERROR) from error

        if not isinstance(data, dict):
            raise GraphQLStatusError(type_error_msg, status=400, code=error_codes.DECODING_ERROR)
        return data

    @classmethod
    def parse_json_body(cls, body: bytes, charset: str = "utf-8") -> dict[str, Any]:
        decoded = cls.decode_body(body, charset=charset)
        return cls.load_json_dict(
            decoded,
            decode_error_msg="Could not load JSON body.",
            type_error_msg="JSON body should convert to a dictionary.",
        )

    @classmethod
    def parse_file_uploads(cls, post_data: dict[str, str], files: dict[str, File]) -> dict[str, Any]:
        operations = cls.get_operations(post_data)
        files_map = cls.get_map(post_data)
        place_files(operations, files_map, files)
        return operations

    @classmethod
    def get_operations(cls, post_data: dict[str, str]) -> dict[str, Any]:  # pragma: no cover
        operations: str | None = post_data.get("operations")
        if not isinstance(operations, str):
            msg = "File upload must contain an `operations` value."
            raise GraphQLStatusError(msg, status=400, code=error_codes.MISSING_OPERATIONS)

        return cls.load_json_dict(
            operations,
            decode_error_msg="The `operations` value must be a JSON object.",
            type_error_msg="The `operations` value is not a mapping.",
        )

    @classmethod
    def get_map(cls, post_data: dict[str, str]) -> dict[str, list[str]]:  # pragma: no cover
        files_map_str: str | None = post_data.get("map")
        if not isinstance(files_map_str, str):
            msg = "File upload must contain an `map` value."
            raise GraphQLStatusError(msg, status=400, code=error_codes.MISSING_FILE_MAP)

        files_map = cls.load_json_dict(
            files_map_str,
            decode_error_msg="The `map` value must be a JSON object.",
            type_error_msg="The `map` value is not a mapping.",
        )

        for value in files_map.values():
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                msg = "The `map` value is not a mapping from string to list of strings."
                raise GraphQLStatusError(msg, status=400, code=error_codes.DECODING_ERROR)

        return files_map

    @classmethod
    def get_graphql_params(cls, data: dict[str, str]) -> GraphQLParams:
        query: str | None = data.get("query")
        if not query or query == "null":
            msg = "Requests must contain a `query` string describing the graphql document."
            raise GraphQLStatusError(msg, status=400, code=error_codes.EMPTY_QUERY)

        operation_name: str | None = data.get("operationName") or None

        variables: str | None = data.get("variables")
        if isinstance(variables, str):
            variables: dict[str, str] = cls.load_json_dict(
                variables,
                decode_error_msg="Variables are invalid JSON.",
                type_error_msg="Variables must be a mapping.",
            )

        extensions: str | None = data.get("extensions")
        if isinstance(extensions, str):
            extensions: dict[str, str] = cls.load_json_dict(
                extensions,
                decode_error_msg="Extensions are invalid JSON.",
                type_error_msg="Extensions must be a mapping.",
            )

        return GraphQLParams(
            query=query,
            variables=variables,
            operation_name=operation_name,
            extensions=extensions,
        )
