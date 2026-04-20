from __future__ import annotations

import asyncio
from unittest.mock import patch

from django.http import HttpResponse
from django.http.request import MediaType

from tests.helpers import MockRequest
from undine.http.content_negotiation import (
    add_media_type_param,
    get_preferred_response_content_type,
    media_type_match,
    media_type_quality,
    require_graphql_request_async,
    require_graphql_request_sync,
    require_persisted_documents_request,
)
from undine.http.responses import HttpMethodNotAllowedResponse, HttpUnsupportedContentTypeResponse

# ---- require_graphql_request_sync ----


def test_require_graphql_request_sync__unsupported_content_type(undine_settings) -> None:
    undine_settings.GRAPHIQL_ENABLED = False

    @require_graphql_request_sync
    def view(request):
        return "should not reach"

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("text/xml")],
    )
    response = view(request)

    assert isinstance(response, HttpUnsupportedContentTypeResponse)
    assert response.status_code == 406


def test_require_graphql_request_sync__get_graphiql(undine_settings) -> None:
    undine_settings.GRAPHIQL_ENABLED = True

    @require_graphql_request_sync
    def view(request):
        return "should not reach"

    request = MockRequest(
        method="GET",
        accepted_types=[MediaType("text/html")],
    )
    response = view(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]


# ---- require_graphql_request_async ----


def test_require_graphql_request_async__method_not_allowed(undine_settings) -> None:
    undine_settings.GRAPHIQL_ENABLED = False

    @require_graphql_request_async
    async def view(request):  # noqa: RUF029
        return "should not reach"

    request = MockRequest(
        method="DELETE",
        accepted_types=[MediaType("application/json")],
    )
    response = asyncio.run(view(request))

    assert isinstance(response, HttpMethodNotAllowedResponse)
    assert response.status_code == 405
    assert response["Allow"] == "GET, POST"


def test_require_graphql_request_async__get_graphiql_enabled_appends_text_html(undine_settings) -> None:
    undine_settings.GRAPHIQL_ENABLED = True

    @require_graphql_request_async
    async def view(request):  # noqa: RUF029
        return "reached"

    request = MockRequest(
        method="GET",
        accepted_types=[MediaType("text/html")],
    )
    response = asyncio.run(view(request))

    # text/html should match and render GraphiQL

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]


def test_require_graphql_request_async__unsupported_content_type(undine_settings) -> None:
    undine_settings.GRAPHIQL_ENABLED = False

    @require_graphql_request_async
    async def view(request):  # noqa: RUF029
        return "should not reach"

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("text/xml")],
    )
    response = asyncio.run(view(request))

    assert isinstance(response, HttpUnsupportedContentTypeResponse)
    assert response.status_code == 406


def test_require_graphql_request_async__get_renders_graphiql(undine_settings) -> None:
    undine_settings.GRAPHIQL_ENABLED = True

    @require_graphql_request_async
    async def view(request):  # noqa: RUF029
        return "should not reach"

    request = MockRequest(
        method="GET",
        accepted_types=[MediaType("text/html")],
    )
    response = asyncio.run(view(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]


# ---- require_persisted_documents_request ----


def test_require_persisted_documents_request__method_not_allowed(undine_settings) -> None:

    @require_persisted_documents_request
    def view(request):
        return "should not reach"

    request = MockRequest(
        method="GET",
        accepted_types=[MediaType("application/json")],
    )
    response = view(request)

    assert isinstance(response, HttpMethodNotAllowedResponse)
    assert response.status_code == 405
    assert response["Allow"] == "POST"


# ---- get_preferred_response_content_type ----


def test_get_preferred_response_content_type__no_accepted_types() -> None:
    result = get_preferred_response_content_type(
        accepted=[],
        supported=["application/json"],
    )
    assert result is None


def test_get_preferred_response_content_type__no_supported_types() -> None:
    result = get_preferred_response_content_type(
        accepted=[MediaType("application/json")],
        supported=[],
    )
    assert result is None


# ---- media_type_match ----


def test_media_type_match__string_self() -> None:
    result = media_type_match("application/json", MediaType("application/json"))
    assert result is True


def test_media_type_match__string_other() -> None:
    result = media_type_match(MediaType("application/json"), "application/json")
    assert result is True


def test_media_type_match__empty_sub_type_returns_false() -> None:
    # 'application/' has empty sub_type, so all() returns False
    result = media_type_match(MediaType("application/"), MediaType("application/json"))
    assert result is False


def test_media_type_match__empty_main_type_returns_false() -> None:
    result = media_type_match(MediaType("/json"), MediaType("application/json"))
    assert result is False


def test_media_type_match__different_main_types() -> None:
    result = media_type_match(MediaType("text/plain"), MediaType("application/json"))
    assert result is False


# ---- media_type_quality ----


def test_media_type_quality__invalid_q_value() -> None:
    media_type = MediaType("application/json;q=invalid")
    result = media_type_quality(media_type)
    assert result == 1


def test_media_type_quality__q_value_out_of_range_negative() -> None:
    media_type = MediaType("application/json;q=-0.5")
    result = media_type_quality(media_type)
    assert result == 1


def test_media_type_quality__q_value_out_of_range_high() -> None:
    media_type = MediaType("application/json;q=1.5")
    result = media_type_quality(media_type)
    assert result == 1


# ---- add_media_type_param ----


def test_add_media_type_param__deletes_cached_range_params() -> None:
    media_type = MediaType("multipart/mixed; subscriptionSpec=1.0")
    # Force the cached property to be stored in __dict__
    _ = media_type.range_params
    assert "range_params" in media_type.__dict__

    result = add_media_type_param(media_type, name="boundary", value="graphql")

    # After add_media_type_param the cache should be cleared
    assert "range_params" not in result.__dict__
    assert result.params["boundary"] == "graphql"


def test_require_graphql_request_sync__html_post_method_not_allowed(undine_settings) -> None:

    @require_graphql_request_sync
    def view(request):
        return "should not reach"

    request = MockRequest(method="POST", accepted_types=[MediaType("text/html")])

    path = "undine.http.content_negotiation.get_preferred_response_content_type"
    with patch(path, return_value=MediaType("text/html")):
        response = view(request)

    assert isinstance(response, HttpMethodNotAllowedResponse)
    assert response.status_code == 405


def test_require_graphql_request_async__html_post_method_not_allowed(undine_settings) -> None:

    @require_graphql_request_async
    async def view(request):  # noqa: RUF029
        return "should not reach"

    request = MockRequest(method="POST", accepted_types=[MediaType("text/html")])

    path = "undine.http.content_negotiation.get_preferred_response_content_type"
    with patch(path, return_value=MediaType("text/html")):
        response = asyncio.run(view(request))

    assert isinstance(response, HttpMethodNotAllowedResponse)
    assert response.status_code == 405


def test_media_type_match__empty_other_string() -> None:
    result = media_type_match(MediaType("application/json"), "")
    assert result is False
