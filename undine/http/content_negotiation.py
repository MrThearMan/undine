from __future__ import annotations

import operator
from functools import wraps
from http import HTTPStatus
from typing import TYPE_CHECKING, Literal, NamedTuple

from django.http.request import MediaType
from django.http.response import ResponseHeaders
from graphql import version_info

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

        # 'test/html' is reserved for GraphiQL which must use GET
        if media_type_match(media_type, text_html):
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
            *(
                (multipart_incremental,)
                if undine_settings.EXPERIMENTAL_INCREMENTAL_DELIVERY and version_info >= (3, 3, 0)
                else ()
            ),
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

        # 'test/html' is reserved for GraphiQL which must use GET
        if media_type_match(media_type, text_html):
            if request.method != "GET":
                return HttpMethodNotAllowedResponse(allowed_methods=["GET"])
            return render_graphiql(request)  # type: ignore[arg-type]

        if media_type_match(media_type, multipart_subscription) or media_type_match(media_type, multipart_incremental):
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
    :param all_types_override: Is accepted type is '*/*', match this type instead of the first supported type.
    """
    if not supported or not accepted:
        return None

    preference: dict[str, PreferenceOrder] = {}

    for accept_order, accepted_type in enumerate(accepted):
        if all_types_override and media_type_specificity(accepted_type) == 0:
            preference.setdefault(
                all_types_override,
                PreferenceOrder(
                    quality_neg=-media_type_quality(accepted_type),
                    specificity_neg=-media_type_specificity(accepted_type),
                    support_order=0,
                    accept_order=accept_order,
                ),
            )
            continue

        for support_order, supported_type in enumerate(supported):
            if media_type_match(accepted_type, supported_type):
                preference.setdefault(
                    supported_type,
                    PreferenceOrder(
                        quality_neg=-media_type_quality(accepted_type),
                        specificity_neg=-media_type_specificity(accepted_type),
                        support_order=support_order,
                        accept_order=accept_order,
                    ),
                )
                break

    if not preference:
        return None

    return MediaType(min(preference, key=preference.get))  # type: ignore[arg-type]


def media_type_match(self: MediaType | str, other: MediaType | str) -> bool:
    """Port of Django>=5.2 `MediaType.match` method."""
    if not other:
        return False

    if not isinstance(self, MediaType):
        self = MediaType(self)

    if not isinstance(other, MediaType):
        other = MediaType(other)

    main_types = [self.main_type, other.main_type]
    sub_types = [self.sub_type, other.sub_type]

    if not all((*main_types, *sub_types)):
        return False

    for this_type, other_type in (main_types, sub_types):
        if this_type not in {other_type, "*"} and other_type != "*":
            return False

    self_range_params = media_type_range_params(self)
    other_range_params = media_type_range_params(other)

    if bool(self_range_params) == bool(other_range_params):
        return self_range_params == other_range_params
    return bool(self_range_params or not other_range_params)


def media_type_quality(media_type: MediaType, /) -> float:
    """Port of Django>=5.2 `MediaType.quality` property."""
    try:
        quality = float(media_type.params.get("q", 1))
    except ValueError:
        return 1
    if quality < 0 or quality > 1:
        return 1
    return round(quality, 3)


def media_type_specificity(media_type: MediaType, /) -> Literal[0, 1, 2, 3]:
    """Port of Django>=5.2 `MediaType.specificity` property."""
    if media_type.main_type == "*":
        return 0
    if media_type.sub_type == "*":
        return 1
    if not media_type_range_params(media_type):
        return 2
    return 3


def media_type_range_params(media_type: MediaType, /) -> dict[str, bytes | str]:
    """Port of Django>=5.2 `MediaType.range_params` property."""
    range_params = media_type.params.copy()
    range_params.pop("q", None)
    return range_params  # type: ignore[return-value]


def add_media_type_param(media_type: MediaType, *, name: str, value: str) -> MediaType:
    """Add a parameter to the given media type."""
    media_type.params[name] = value  # type: ignore[assignment]

    # Sort the parameters to ensure a consistent order
    media_type.params = dict(sorted(media_type.params.items(), key=operator.itemgetter(0)))

    # 'range_params' is a cached property, so we need to delete it to force a re-calculation
    if "range_params" in media_type.__dict__:
        del media_type.__dict__["range_params"]

    return media_type
