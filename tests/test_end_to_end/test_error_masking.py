from __future__ import annotations

import logging

from undine import Entrypoint, RootType, create_schema
from undine.exceptions import GraphQLPermissionError
from undine.utils.graphql.utils import never_mask_error


def test_end_to_end__error_masking__unexpected_exception(graphql, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def secret(self) -> str:
            msg = "DB password is hunter2 at db.internal:5432"
            raise RuntimeError(msg)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { secret }")

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Unexpected error.",
                "path": ["secret"],
                "extensions": {"status_code": 500},
            },
        ],
    }
    assert b"hunter2" not in response.response.content


def test_end_to_end__error_masking__disabled(graphql, undine_settings) -> None:
    undine_settings.ERROR_MASKING_PREDICATE = never_mask_error

    class Query(RootType):
        @Entrypoint
        def secret(self) -> str:
            msg = "DB password is hunter2 at db.internal:5432"
            raise RuntimeError(msg)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { secret }")

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "DB password is hunter2 at db.internal:5432",
                "path": ["secret"],
                "extensions": {"status_code": 500},
            },
        ],
    }


def test_end_to_end__error_masking__non_nullable_field_violation(graphql, undine_settings) -> None:
    """graphql-core reports this one by raising a plain `TypeError`, so it is masked like any other."""

    class Query(RootType):
        @Entrypoint
        def name(self) -> str:
            return None  # type: ignore[return-value]

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { name }")

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Unexpected error.",
                "path": ["name"],
                "extensions": {"status_code": 500},
            },
        ],
    }


def test_end_to_end__error_masking__permission_error(graphql, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def secret(self) -> str:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { secret }")

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "path": ["secret"],
                "extensions": {"status_code": 403, "error_code": "PERMISSION_DENIED"},
            },
        ],
    }


def test_end_to_end__error_masking__traceback_not_sent_but_logged(graphql, undine_settings, caplog) -> None:
    undine_settings.INCLUDE_ERROR_TRACEBACK = True

    class Query(RootType):
        @Entrypoint
        def secret(self) -> str:
            msg = "DB password is hunter2 at db.internal:5432"
            raise RuntimeError(msg)

    undine_settings.SCHEMA = create_schema(query=Query)

    with caplog.at_level(logging.DEBUG, logger="undine"):
        response = graphql("query { secret }")

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Unexpected error.",
                "path": ["secret"],
                "extensions": {"status_code": 500},
            },
        ],
    }

    messages = [record.message for record in caplog.records]
    assert "Masked error: DB password is hunter2 at db.internal:5432" in messages
    assert any("raise RuntimeError(msg)" in message for message in messages)
