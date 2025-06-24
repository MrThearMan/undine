from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from graphql import ExecutionResult, GraphQLError

from undine.exceptions import GraphQLErrorGroup, GraphQLRequestDecodingError
from undine.http.utils import (
    graphql_error_group_response,
    graphql_error_response,
    graphql_result_response,
    parse_json_body,
    require_persisted_documents_request,
)
from undine.settings import undine_settings

from .utils import parse_document_map, register_persisted_documents

if TYPE_CHECKING:
    from undine.typing import DjangoRequestProtocol, DjangoResponseProtocol

__all__ = [
    "persisted_documents_view",
]


@require_persisted_documents_request
def persisted_documents_view(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    """
    View for registering persisted documents.
    Users should add permission checks.
    """
    try:
        json_data = parse_json_body(request.body)
    except GraphQLRequestDecodingError as error:
        return graphql_error_response(error, status=HTTPStatus.BAD_REQUEST)

    try:
        document_map = parse_document_map(json_data)
    except GraphQLErrorGroup as error:
        return graphql_error_group_response(error, status=HTTPStatus.BAD_REQUEST)

    if undine_settings.PERSISTED_DOCUMENTS_PERMISSION_CALLBACK is not None:
        try:
            undine_settings.PERSISTED_DOCUMENTS_PERMISSION_CALLBACK(request, document_map)
        except GraphQLError as error:
            return graphql_error_response(error, status=HTTPStatus.FORBIDDEN)
        except GraphQLErrorGroup as error:
            return graphql_error_group_response(error, status=HTTPStatus.FORBIDDEN)

    try:
        document_id_map = register_persisted_documents(document_map)
    except GraphQLErrorGroup as error:
        return graphql_error_group_response(error, status=HTTPStatus.BAD_REQUEST)

    result = ExecutionResult(data={"documents": document_id_map})
    return graphql_result_response(result)
