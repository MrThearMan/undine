from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from undine.dataclasses import GraphQLParams
from undine.schema import execute_graphql

from .models import PersistedQuery

__all__ = [
    "execute_persisted_query",
]


@require_POST
def execute_persisted_query(request: HttpRequest, name: str) -> JsonResponse:
    persisted_query = get_object_or_404(PersistedQuery, name=name)

    params = GraphQLParams(
        query=persisted_query.document,
        variables=request.POST.dict(),
    )

    result = execute_graphql(params=params, method="POST", context_value=request)
    return JsonResponse(data=result.formatted, status=200)
