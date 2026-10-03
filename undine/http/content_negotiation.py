from __future__ import annotations

import operator
from functools import wraps
from http import HTTPStatus
from typing import TYPE_CHECKING, NamedTuple

from django.http.request import MediaType
from django.http.response import ResponseHeaders

from undine.exceptions import GraphQLMissingContentTypeError, GraphQLUnsupportedContentTypeError
from undine.http.responses import (
    HttpMethodNotAllowedResponse,
    HttpUnsupportedContentTypeResponse,
    graphql_result_response,
)
from undine.integrations.graphiql import render_graphiql
from undine.settings import undine_settings
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from django.http import HttpResponse

    from undine.typing import (
        AsyncViewIn,
        AsyncViewOut,
        DjangoRequestProtocol,
        DjangoResponseProtocol,
        RequestMethod,
        SyncViewIn,
        SyncViewOut,
    )

__all__ = [
    "add_media_type_param",
    "get_preferred_response_content_type",
    "require_graphql_request_async",
    "require_graphql_request_sync",
    "require_persisted_documents_request",
]


def require_graphql_request_sync(func: SyncViewIn) -> SyncViewOut:
    """
    Perform various checks on the request to ensure it's suitable for GraphQL operations in a synchronous server.
    Can also return early to display GraphiQL.
    """
    allowed_methods: list[RequestMethod] = ["GET", "POST"]

    application_graphql = "application/graphql-response+json"
    application_json = "application/json"
    text_html = "text/html"

    @wraps(func)
    def wrapper(request: DjangoRequestProtocol) -> DjangoResponseProtocol | HttpResponse:
        if request.method not in allowed_methods:
            return HttpMethodNotAllowedResponse(allowed_methods=allowed_methods)

        supported_types = [
            application_graphql,
            application_json,
        ]
        if request.method == "GET" and undine_settings.GRAPHIQL_ENABLED:
            supported_types.append(text_html)

        media_type = get_preferred_response_content_type(accepted=request.accepted_types, supported=supported_types)
        if media_type is None:
            return HttpUnsupportedContentTypeResponse(supported_types=supported_types)

        # 'text/html' is reserved for GraphiQL which must use GET
        if media_type.match(text_html):
            if request.method != "GET":
                return HttpMethodNotAllowedResponse(allowed_methods=["GET"])
            return render_graphiql(request)  # type: ignore[arg-type]

        request.response_content_type = media_type
        request.response_headers = ResponseHeaders({})
        return func(request)  # type: ignore[return-value]

    return wrapper  # type: ignore[return-value]


def require_graphql_request_async(func: AsyncViewIn) -> AsyncViewOut:
    """
    Perform various checks on the request to ensure it's suitable for GraphQL operations in an asynchronous server.
    Can also return early to display GraphiQL.
    """
    allowed_methods: list[RequestMethod] = ["GET", "POST"]

    event_stream = "text/event-stream"
    multipart_subscription = "multipart/mixed; subscriptionSpec=1.0"
    multipart_incremental = "multipart/mixed"
    application_graphql = "application/graphql-response+json"
    application_json = "application/json"
    text_html = "text/html"

    @wraps(func)
    async def wrapper(request: DjangoRequestProtocol) -> DjangoResponseProtocol | HttpResponse:
        if request.method not in allowed_methods:
            return HttpMethodNotAllowedResponse(allowed_methods=allowed_methods)

        supported_types = [
            event_stream,
            multipart_subscription,
            *((multipart_incremental,) if undine_settings.EXPERIMENTAL_INCREMENTAL_DELIVERY else ()),
            application_graphql,
            application_json,
        ]
        if request.method == "GET" and undine_settings.GRAPHIQL_ENABLED:
            supported_types.append(text_html)

        media_type = get_preferred_response_content_type(
            accepted=request.accepted_types,
            supported=supported_types,
            all_types_override=application_json,
        )
        if media_type is None:
            return HttpUnsupportedContentTypeResponse(supported_types=supported_types)

        # 'text/html' is reserved for GraphiQL which must use GET
        if media_type.match(text_html):
            if request.method != "GET":
                return HttpMethodNotAllowedResponse(allowed_methods=["GET"])
            return render_graphiql(request)  # type: ignore[arg-type]

        if media_type.match(multipart_subscription) or media_type.match(multipart_incremental):
            add_media_type_param(media_type, name="boundary", value="graphql")

        request.response_content_type = media_type
        request.response_headers = ResponseHeaders({})
        return await func(request)

    return wrapper  # type: ignore[return-value]


def require_persisted_documents_request(func: SyncViewIn) -> SyncViewOut:
    """Perform various checks on the request to ensure that it's suitable for registering persisted documents."""
    methods: list[RequestMethod] = ["POST"]

    application_json = "application/json"

    @wraps(func)
    def wrapper(request: DjangoRequestProtocol) -> DjangoResponseProtocol | HttpResponse:
        if request.method not in methods:
            return HttpMethodNotAllowedResponse(allowed_methods=methods)

        media_type = get_preferred_response_content_type(accepted=request.accepted_types, supported=[application_json])
        if media_type is None:
            return HttpUnsupportedContentTypeResponse(supported_types=[application_json])

        request.response_content_type = media_type

        if request.content_type is None:  # pragma: no cover
            result = get_error_execution_result(GraphQLMissingContentTypeError())
            return graphql_result_response(result, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE, content_type=media_type)

        if not MediaType(request.content_type).match(application_json):
            result = get_error_execution_result(GraphQLUnsupportedContentTypeError(content_type=request.content_type))
            return graphql_result_response(result, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE, content_type=media_type)

        return func(request)

    return wrapper  # type: ignore[return-value]


class PreferenceOrder(NamedTuple):
    # Fields in order of importance to preference
    quality_neg: float
    specificity_neg: int
    support_order: int
    accept_order: int


def get_preferred_response_content_type(
    *,
    accepted: list[MediaType],
    supported: list[str],
    all_types_override: str | None = None,
) -> MediaType | None:
    """
    Get the preferred and best supported media type matching given accepted types.

    Preference order is determined using these rules in order:
    1. The higher the quality (;q={0-1}), the higher the preference.
    2. The higher the specificity (text/plain;param=1 > text/plain > text/* > */*), the higher the preference.
    3. If one accepted type is before another in the supported list, that one has higher preference.
    4. As a final fallback, prefer the accepted type that is listed first by the client.

    :param accepted: The accepted media types by the client.
    :param supported: The supported media types, in order of preference.
    :param all_types_override: If accepted type is '*/*', match this type instead of the first supported type.
    """
    if not supported or not accepted:
        return None

    preference: dict[str, PreferenceOrder] = {}

    for accept_order, accepted_type in enumerate(accepted):
        if all_types_override and accepted_type.specificity == 0:
            preference.setdefault(
                all_types_override,
                PreferenceOrder(
                    quality_neg=-accepted_type.quality,
                    specificity_neg=-accepted_type.specificity,
                    support_order=0,
                    accept_order=accept_order,
                ),
            )
            continue

        for support_order, supported_type in enumerate(supported):
            if accepted_type.match(supported_type):
                preference.setdefault(
                    supported_type,
                    PreferenceOrder(
                        quality_neg=-accepted_type.quality,
                        specificity_neg=-accepted_type.specificity,
                        support_order=support_order,
                        accept_order=accept_order,
                    ),
                )
                break

    if not preference:
        return None

    return MediaType(min(preference, key=preference.get))  # type: ignore[arg-type]


def add_media_type_param(media_type: MediaType, *, name: str, value: str) -> MediaType:
    """Add a parameter to the given media type."""
    media_type.params[name] = value  # type: ignore[assignment]

    # Sort the parameters to ensure a consistent order
    media_type.params = dict(sorted(media_type.params.items(), key=operator.itemgetter(0)))

    # 'range_params' is a cached property, so we need to delete it to force a re-calculation
    if "range_params" in media_type.__dict__:
        del media_type.__dict__["range_params"]

    return media_type
