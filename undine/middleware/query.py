from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from django.db.models import Model

    from undine import Field, QueryType
    from undine.typing import GQLInfo, QueryResult


__all__ = [
    "QueryMiddleware",
    "QueryMiddlewareHandler",
    "QueryPermissionCheckMiddleware",
]


class QueryMiddleware:
    """
    Base class for query middleware.

    QueryMiddlewares are run for each QueryType's resolver,
    so they should only focus on that QueryType.
    """

    priority: int
    """Middleware priority. Lower number means middleware context is entered earlier in the middleware stack."""

    def __init__(
        self,
        *,
        root: Model | None,
        info: GQLInfo,
        query_type: type[QueryType],
        field: Field | None = None,
        many: bool = False,
    ) -> None:
        """
        Initialize the middleware.

        :param root: The root value for the query.
        :param info: The GraphQL resolve info for the request.
        :param query_type: The QueryType that is being executed.
        :param field: The undine.Field being queried.
        :param many: Whether the query is for a list of items.
        """
        self.root = root
        self.root_info = info
        self.query_type = query_type
        self.field = field
        self.many = many

    def before(self) -> None:
        """Stuff that happens before the query is executed."""

    def after(self, value: QueryResult) -> None:
        """Stuff that happens after the query is executed."""

    def exception(self, exc: Exception) -> None:
        """Stuff that happens if an exception is raised during the query."""


class QueryPermissionCheckMiddleware(QueryMiddleware):
    """
    Query middleware required for permissions checks to work.

    Runs permission checks for the given QueryType.
    """

    priority = 100

    def before(self) -> None:
        if self.root is not None and self.field is not None and self.field.permissions_func is not None:
            self.field.permissions_func(self.field, self.root_info, self.root)

    def after(self, value: QueryResult) -> None:
        if value is None:
            return

        if self.field is not None and self.field.skip_query_type_perms:
            return

        if self.many:
            self.query_type.__permissions_many__(value, self.root_info)
        else:
            self.query_type.__permissions_single__(value, self.root_info)


class QueryMiddlewareHandler:
    """
    Executes defined middlewares for a QueryType.

    All middleware have three possible steps:
    - a before step, which is run before the query
    - an after step, which is run after the query (if successful)
    - an exception step, which is run if an exception is raised during the query

    The middleware with the highest priority (lowest number) has its before step run first
    and after or exception steps last.
    """

    def __init__(
        self,
        root: Any,
        info: GQLInfo,
        query_type: type[QueryType],
        *,
        field: Field | None = None,
        many: bool = False,
    ) -> None:
        """
        Initialize the middleware handler.

        :param root: The root value for the query.
        :param info: The GraphQL resolve info for the request.
        :param query_type: The QueryType that is being executed.
        :param field: The undine.Field being queried.
        :param many: Whether the query is for a list of items.
        """
        self.middleware: list[QueryMiddleware] = [
            middleware(
                root=root,
                info=info,
                query_type=query_type,
                field=field,
                many=many,
            )
            for middleware in sorted(query_type.__middleware__(), key=lambda m: (m.priority, m.__name__))
        ]

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
