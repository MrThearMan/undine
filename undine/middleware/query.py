from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

from django.db import models

from undine.dataclasses import QueryMiddlewareParams
from undine.errors.exceptions import GraphQLPermissionDeniedError

if TYPE_CHECKING:
    from undine import Field, QueryType
    from undine.typing import GQLInfo, QueryResult


__all__ = [
    "QueryMiddleware",
    "QueryMiddlewareHandler",
    "QueryPermissionCheckMiddleware",
]


class QueryMiddleware:
    """Base class for query middleware."""

    priority: int
    """Middleware priority. Lower number means middleware context is entered earlier in the middleware stack."""

    def __init__(self, params: QueryMiddlewareParams) -> None:
        self.params = params

    def before(self) -> None:
        """Stuff that happens before the query is executed."""

    def after(self, value: QueryResult) -> None:
        """Stuff that happens after the query is executed."""

    def exception(self, exc: Exception) -> None:
        """Stuff that happens if an exception is raised during the query."""


class QueryPermissionCheckMiddleware(QueryMiddleware):
    """
    Query middleware required for permissions checks to work.

    Runs permission checks for the given query type.
    """

    priority = 100

    def before(self) -> None:
        if self.params.root is None or self.params.field is None or self.params.field.permissions_func is None:
            return

        if self.params.field.permissions_func(self.params.field, self.params.info, self.params.root):
            return

        raise GraphQLPermissionDeniedError

    def after(self, value: QueryResult) -> None:
        if value is None:
            return

        if self.params.field is not None and self.params.field.skip_query_type_perms:
            return

        if isinstance(value, models.Model):
            if not self.params.query_type.__permission_single__(value, self.params.info):
                raise GraphQLPermissionDeniedError
            return

        if isinstance(value, list):
            if not self.params.query_type.__permission_many__(value, self.params.info):
                raise GraphQLPermissionDeniedError
            return


class QueryMiddlewareHandler:
    """
    Executes defined middlewares for a QueryType.

    All middleware have three possible steps:
    - a before step, which is run before the query
    - an after step, which is run after the query
    - an exception step, which is run if an exception is raised during the query

    The middleware with the highest priority (lowest number) has its before step run first
    and after or exception steps last.
    """

    def __init__(
        self,
        root: Any,
        info: GQLInfo,
        query_type: type[QueryType],
        field: Field | None = None,
    ) -> None:
        self.middleware: list[QueryMiddleware] = []
        self.params = QueryMiddlewareParams(query_type=query_type, info=info, field=field, root=root)

        sorted_middleware = sorted(query_type.__middleware__(), key=lambda m: (m.priority, m.__name__))

        for middleware in sorted_middleware:
            self.middleware.append(middleware(self.params))

    def wrap(self, func: Callable[[], QueryResult], /) -> Callable[[], QueryResult]:
        """Wraps a query function with the middleware."""

        @wraps(func)
        def wrapper() -> QueryResult:
            for middleware in self.middleware:
                middleware.before()

            try:
                value = func()
            except Exception as exc:
                for middleware in reversed(self.middleware):
                    middleware.exception(exc)
                raise
            else:
                for middleware in reversed(self.middleware):
                    middleware.after(value)

            return value

        return wrapper
