from __future__ import annotations

import pytest

from tests.test_integrations.test_channels.helpers import get_graphql_sse_router, make_http_scope

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


async def test_channels__sse_router__non_graphql_path_routes_to_asgi() -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(path="/other/")

    await router(scope, None, None)

    router.django_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__put_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="PUT",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__delete_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="DELETE",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__get_with_token_query_param_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="GET",
        query_string=b"token=some-token",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__get_with_token_header_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="GET",
        headers=[(b"x-graphql-event-stream-token", b"some-token")],
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__post_with_token_query_param_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="POST",
        query_string=b"token=some-token",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__post_with_token_header_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="POST",
        headers=[(b"x-graphql-event-stream-token", b"some-token")],
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__get_without_token_routes_to_asgi(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="GET",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.django_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__post_without_token_routes_to_asgi(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="POST",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.django_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()


async def test_channels__sse_router__other_method_routes_to_asgi() -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(method="PATCH")  # type: ignore[arg-type]

    await router(scope, None, None)

    router.django_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()
