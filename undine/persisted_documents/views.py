from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from django.http import JsonResponse
from django.views import View
from django.views.decorators.http import require_POST

from undine.exceptions import GraphQLErrorGroup, GraphQLRequestDecodingError
from undine.http.utils import parse_json_body, require_json

from .utils import parse_document_map, register_persisted_documents

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

__all__ = [
    "PersistedDocumentsView",
]


class PersistedDocumentsView(View):
    """
    View for registering persisted documents.
    Users should extend this view to add permission checks.
    """

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return _persisted_documents_view_impl(request)


@require_POST
@require_json
def _persisted_documents_view_impl(request: HttpRequest) -> HttpResponse:
    try:
        json_data = parse_json_body(request.body)
    except GraphQLRequestDecodingError as error:
        return JsonResponse(data={"errors": [error.formatted]}, status=HTTPStatus.BAD_REQUEST)

    try:
        document_map = parse_document_map(json_data)
    except GraphQLErrorGroup as error:
        errors = [error.formatted for error in error.flatten()]
        return JsonResponse(data={"errors": errors}, status=HTTPStatus.BAD_REQUEST)

    try:
        document_id_map = register_persisted_documents(document_map)
    except GraphQLErrorGroup as error:
        errors = [error.formatted for error in error.flatten()]
        return JsonResponse(data={"errors": errors}, status=HTTPStatus.BAD_REQUEST)

    return JsonResponse(data={"documents": document_id_map}, status=HTTPStatus.OK)
