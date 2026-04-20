from __future__ import annotations

import asyncio
from typing import NamedTuple
from unittest.mock import patch

import pytest
from django.http import HttpResponse
from django.http.request import MediaType

from tests.helpers import MockRequest, parametrize_helper
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

# Sync


def test_require_graphql_request_sync__unsupported_content_type(undine_settings) -> None:
    undine_settings.GRAPHIQL_ENABLED = False

    @require_graphql_request_sync
    def view(request):
        pytest.fail("should not reach")

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
        pytest.fail("should not reach")

    request = MockRequest(
        method="GET",
        accepted_types=[MediaType("text/html")],
    )
    response = view(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]


def test_require_graphql_request_sync__html_post_method_not_allowed(undine_settings) -> None:

    @require_graphql_request_sync
    def view(request):
        pytest.fail("should not reach")

    request = MockRequest(method="POST", accepted_types=[MediaType("text/html")])

    path = "undine.http.content_negotiation.get_preferred_response_content_type"
    with patch(path, return_value=MediaType("text/html")):
        response = view(request)

    assert isinstance(response, HttpMethodNotAllowedResponse)
    assert response.status_code == 405


# Async


def test_require_graphql_request_async__method_not_allowed(undine_settings) -> None:
    undine_settings.GRAPHIQL_ENABLED = False

    @require_graphql_request_async
    async def view(request):  # noqa: RUF029
        pytest.fail("should not reach")

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
        pytest.fail("should not reach")

    request = MockRequest(
        method="GET",
        accepted_types=[MediaType("text/html")],
    )
    response = asyncio.run(view(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]


def test_require_graphql_request_async__unsupported_content_type(undine_settings) -> None:
    undine_settings.GRAPHIQL_ENABLED = False

    @require_graphql_request_async
    async def view(request):  # noqa: RUF029
        pytest.fail("should not reach")

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("text/xml")],
    )
    response = asyncio.run(view(request))

    assert isinstance(response, HttpUnsupportedContentTypeResponse)
    assert response.status_code == 406


def test_require_graphql_request_async__html_post_method_not_allowed(undine_settings) -> None:

    @require_graphql_request_async
    async def view(request):  # noqa: RUF029
        pytest.fail("should not reach")

    request = MockRequest(method="POST", accepted_types=[MediaType("text/html")])

    path = "undine.http.content_negotiation.get_preferred_response_content_type"
    with patch(path, return_value=MediaType("text/html")):
        response = asyncio.run(view(request))

    assert isinstance(response, HttpMethodNotAllowedResponse)
    assert response.status_code == 405


# Persisted documents


def test_require_persisted_documents_request__method_not_allowed(undine_settings) -> None:

    @require_persisted_documents_request
    def view(request):
        pytest.fail("should not reach")

    request = MockRequest(
        method="GET",
        accepted_types=[MediaType("application/json")],
    )
    response = view(request)

    assert isinstance(response, HttpMethodNotAllowedResponse)
    assert response.status_code == 405
    assert response["Allow"] == "POST"


# Utils


class Input(NamedTuple):
    accepted: list[str]
    supported: list[str]
    all_types_override: str | None
    expected: str


@pytest.mark.parametrize(
    **parametrize_helper({
        "Single accepted type": Input(
            accepted=["application/json"],
            supported=["application/json", "text/html"],
            all_types_override=None,
            expected="application/json",
        ),
        "Any type": Input(
            accepted=["*/*"],
            supported=["application/json", "text/html"],
            all_types_override=None,
            expected="application/json",
        ),
        "Not supported type": Input(
            accepted=["application/json"],
            supported=["text/html"],
            all_types_override=None,
            expected="None",
        ),
        "Any type with override": Input(
            accepted=["*/*"],
            supported=["application/json", "text/html"],
            all_types_override="text/html",
            expected="text/html",
        ),
        "No any type with override": Input(
            accepted=["application/json"],
            supported=["application/json", "text/html"],
            all_types_override="text/html",
            expected="application/json",
        ),
        "With override but has more specific accepted type": Input(
            accepted=["application/json", "*/*"],
            supported=["application/json", "text/html"],
            all_types_override="text/html",
            expected="application/json",
        ),
        "Two types select first supported one": Input(
            accepted=["text/html", "application/json"],
            supported=["application/json", "text/html"],
            all_types_override=None,
            expected="application/json",
        ),
        "Two types select one with higher quantity": Input(
            accepted=["application/json", "text/html;q=0.8"],
            supported=["text/html", "application/json"],
            all_types_override=None,
            expected="application/json",
        ),
        "Two types select one with higher specificity": Input(
            accepted=["application/json", "text/*"],
            supported=["text/html", "application/json"],
            all_types_override=None,
            expected="application/json",
        ),
        "Two types select one without parameters": Input(
            accepted=["application/json", "multipart/mixed"],
            supported=["multipart/mixed;subscriptionSpec=1.0", "multipart/mixed", "application/json"],
            all_types_override=None,
            expected="multipart/mixed",
        ),
        "Two types select one with matching parameters": Input(
            accepted=["multipart/mixed;subscriptionSpec=1.0"],
            supported=["multipart/mixed;subscriptionSpec=1.0", "multipart/mixed", "application/json"],
            all_types_override=None,
            expected="multipart/mixed; subscriptionspec=1.0",
        ),
        "No accepted type": Input(
            accepted=[],
            supported=["application/json"],
            all_types_override=None,
            expected="None",
        ),
        "No supported type": Input(
            accepted=["application/json"],
            supported=[],
            all_types_override=None,
            expected="None",
        ),
    })
)
def test_get_preferred_response_content_type(accepted, supported, all_types_override, expected):
    content_type = get_preferred_response_content_type(
        accepted=[MediaType(at) for at in accepted],
        supported=supported,
        all_types_override=all_types_override,
    )
    assert str(content_type) == expected


@pytest.mark.parametrize(
    ("match", "other", "expected"),
    [
        ("application/json", "application/json", True),
        ("application/json", MediaType("application/json"), True),
        (MediaType("application/json"), "application/json", True),
        (MediaType("application/"), MediaType("application/json"), False),
        (MediaType("/json"), MediaType("application/json"), False),
        (MediaType("text/plain"), MediaType("application/json"), False),
        (MediaType("application/json"), "", False),
    ],
)
def test_media_type_match(match, other, expected):
    result = media_type_match(match, other)
    assert result is expected


@pytest.mark.parametrize(
    ("media_type", "expected"),
    [
        (MediaType("application/json;q=0.8"), 0.8),
        (MediaType("application/json;q=0.0125"), 0.013),
        (MediaType("application/json;q=-0.5"), 1),
        (MediaType("application/json;q=1.5"), 1),
        (MediaType("application/json;q=invalid"), 1),
    ],
)
def test_media_type_quality(media_type, expected):
    result = media_type_quality(media_type)
    assert result == expected


@pytest.mark.skipif(not hasattr(MediaType, "range_params"), reason="`MediaType.range_params` does not exist")
def test_add_media_type_param__deletes_cached_range_params() -> None:
    media_type = MediaType("multipart/mixed; subscriptionSpec=1.0")
    # Force the cached property to be stored in __dict__
    _ = media_type.range_params
    assert "range_params" in media_type.__dict__

    result = add_media_type_param(media_type, name="boundary", value="graphql")

    # After add_media_type_param the cache should be cleared
    assert "range_params" not in result.__dict__
    assert result.params["boundary"] == "graphql"
