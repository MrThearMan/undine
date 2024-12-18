from __future__ import annotations

from copy import deepcopy
from functools import wraps
from types import FunctionType
from typing import TYPE_CHECKING, Any, Callable, ParamSpec, Self

from django.db import IntegrityError, models, transaction
from graphql import Undefined

from undine.dataclasses import MutationMiddlewareParams
from undine.errors.constraints import get_constraint_message
from undine.errors.exceptions import GraphQLModelConstaintViolationError
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from undine import MutationType
    from undine.typing import GQLInfo, JsonObject, QueryResult

__all__ = [
    "AtomicMutationMiddleware",
    "InputDataModificationMiddleware",
    "InputDataValidationMiddleware",
    "InputOnlyDataRemovalMiddleware",
    "IntegrityErrorHandlingMiddleware",
    "MutationMiddleware",
    "MutationMiddlewareHandler",
    "MutationPermissionCheckMiddleware",
    "PostMutationHandlingMiddleware",
]


P = ParamSpec("P")


class MutationMiddleware:
    """Base class for mutation middleware."""

    priority: int
    """Middleware priority. Lower number means middleware context is entered earlier in the middleware stack."""

    def __init__(self, params: MutationMiddlewareParams) -> None:
        self.params = params

    def before(self) -> None:
        """Stuff that happens before the mutation is executed."""

    def after(self, value: QueryResult) -> None:
        """Stuff that happens after the mutation is executed."""

    def exception(self, exc: Exception) -> None:
        """Stuff that happens if an exception is raised during the mutation."""


class InputDataModificationMiddleware(MutationMiddleware):
    """
    Mutation middleware required for hidden input and callable inputs to work.
    Should be executed as the first middleware.

    Alters input data before validation:
     - Adds default values for hidden inputs
     - Calls callable inputs
    """

    priority: int = 0

    def before(self) -> None:
        self.fill_input_data(self.params.mutation_type, self.params.input_data)

    def fill_input_data(self, mutation_type: type[MutationType], input_data: JsonObject) -> None:
        from undine import MutationType  # noqa: PLC0415

        if isinstance(input_data, list):
            for item in input_data:
                self.fill_input_data(mutation_type=mutation_type, input_data=item)
            return

        for field_name, inpt in mutation_type.__input_map__.items():
            value: Any = input_data.get(field_name, Undefined)

            if inpt.hidden and inpt.default_value is not Undefined:
                input_data[field_name] = value = inpt.default_value

            if isinstance(inpt.ref, FunctionType):
                args = () if value is Undefined else (value,)
                input_data[field_name] = value = inpt.ref(inpt, self.params.info, *args)

            # Don't add default values from nested MutationTypes if no other data for it is provided.
            if value is Undefined:
                continue

            if is_subclass(inpt.ref, MutationType):
                self.fill_input_data(mutation_type=inpt.ref, input_data=value)


class MutationPermissionCheckMiddleware(MutationMiddleware):
    """
    Mutation middleware required for permission checks to work.

    Runs permission checks for all QueryTypes and Input fields in the given input data.
    """

    priority: int = 100

    def before(self) -> None:
        if isinstance(self.params.input_data, dict):
            self.check_single_permissions(self.params.mutation_type, self.params.input_data)
        if isinstance(self.params.input_data, list):
            self.check_many_permissions(self.params.mutation_type, self.params.input_data)

    def check_single_permissions(self, mutation_type: type[MutationType], input_data: dict[str, Any]) -> None:
        if mutation_type.__mutation_kind__ == "create":
            mutation_type.__permission_create__(info=self.params.info, input_data=input_data)
            return

        if mutation_type.__mutation_kind__ == "update":
            mutation_type.__permission_delete__(
                info=self.params.info,
                instance=self.params.instance,
                input_data=input_data,
            )
            return

        if mutation_type.__mutation_kind__ == "delete":
            mutation_type.__permission_update__(
                info=self.params.info,
                instance=self.params.instance,
                input_data=input_data,
            )
            return

        mutation_type.__permission_custom__(info=self.params.info, input_data=input_data)

    def check_many_permissions(self, mutation_type: type[MutationType], input_data: list[dict[str, Any]]) -> None:
        lookup_field = self.params.mutation_type.__lookup_field__
        instances_by_pk = {getattr(inst, lookup_field, None): inst for inst in self.params.instances or []}

        for item in input_data:
            if mutation_type.__mutation_kind__ == "create":
                mutation_type.__permission_create__(info=self.params.info, input_data=item)
                continue

            if mutation_type.__mutation_kind__ == "custom":
                mutation_type.__permission_custom__(info=self.params.info, input_data=item)
                continue

            instance = instances_by_pk.get(item.get(lookup_field))
            if instance is None:
                continue

            if mutation_type.__mutation_kind__ == "update":
                mutation_type.__permission_delete__(
                    info=self.params.info,
                    instance=instance,
                    input_data=item,
                )
                continue

            if mutation_type.__mutation_kind__ == "delete":
                mutation_type.__permission_update__(
                    info=self.params.info,
                    instance=instance,
                    input_data=item,
                )
                continue


class InputDataValidationMiddleware(MutationMiddleware):
    """
    Mutation middleware required for input validation to work.

    Run validation for all fields in the given input data.
    """

    priority: int = 200

    def before(self) -> None:
        self.validate_data(self.params.mutation_type, self.params.input_data)

    def validate_data(self, mutation_type: type[MutationType], input_data: dict[str, Any]) -> None:
        from undine import MutationType  # noqa: PLC0415

        if isinstance(input_data, list):
            for item in input_data:
                self.validate_data(mutation_type=mutation_type, input_data=item)
            return

        # Validate all fields individually.
        for field_name, value in input_data.items():
            inpt = mutation_type.__input_map__[field_name]

            if inpt.validator_func is not None:
                inpt.validator_func(inpt, self.params.info, value)

            if is_subclass(inpt.ref, MutationType):
                self.validate_data(mutation_type=inpt.ref, input_data=value)

        # Validate all fields together.
        mutation_type.__validate__(info=self.params.info, input_data=input_data)


class PostMutationHandlingMiddleware(MutationMiddleware):
    """
    Mutation middleware required for post-mutation handling to work.

    Run all `__post_handle__` methods for all MutationTypes based on the mutation input data.
    """

    priority: int = 200

    def after(self, value: QueryResult) -> None:
        # TODO: Do something with value?
        self.post_handling(self.params.mutation_type, self.params.input_data)

    def post_handling(self, mutation_type: type[MutationType], input_data: JsonObject) -> None:
        from undine import MutationType  # noqa: PLC0415

        if isinstance(input_data, list):
            for item in input_data:
                self.post_handling(mutation_type=mutation_type, input_data=item)
            return

        for field_name, value in input_data.items():
            inpt = mutation_type.__input_map__[field_name]

            if is_subclass(inpt.ref, MutationType):
                self.post_handling(mutation_type=inpt.ref, input_data=value)

        mutation_type.__post_handle__(info=self.params.info, input_data=input_data)


class InputOnlyDataRemovalMiddleware(MutationMiddleware):
    """
    Mutation middleware required for input-only fields to work.

    Remove any input-only fields from the given input data.
    Add them back in after the mutation is executed.
    """

    priority: int = 300

    def __init__(self, params: MutationMiddlewareParams) -> None:
        self.original_input_data = deepcopy(params.input_data)
        super().__init__(params)

    def before(self) -> None:
        self.remove_input_only_fields(self.params.mutation_type, self.params.input_data)

    def after(self, value: QueryResult) -> None:
        self.params.input_data = self.original_input_data

    def remove_input_only_fields(self, mutation_type: type[MutationType], input_data: dict[str, Any]) -> None:
        from undine import MutationType  # noqa: PLC0415

        if isinstance(input_data, list):
            for item in input_data:
                self.remove_input_only_fields(mutation_type=mutation_type, input_data=item)
            return

        for field_name in list(input_data):  # Copy keys so that we can .pop() in the loop
            inpt = mutation_type.__input_map__[field_name]

            if is_subclass(inpt.ref, MutationType):
                self.remove_input_only_fields(mutation_type=inpt.ref, input_data=input_data[field_name])

            if inpt.input_only:
                input_data.pop(field_name, None)


class IntegrityErrorHandlingMiddleware(MutationMiddleware):
    """Mutation middleware that converts raised IntegrityErrors from the database to GraphQL errors."""

    # Should run before `AtomicMutationMiddleware` so that if an error occurs,
    # the transaction has already been rolled back before this raises a different error.
    priority: int = 900

    def exception(self, exc: Exception) -> None:
        """If an integrity error occurs, raise a GraphQLStatusError with the appropriate error code."""
        if isinstance(exc, IntegrityError):
            msg = get_constraint_message(exc.args[0])
            raise GraphQLModelConstaintViolationError(msg) from exc


class AtomicMutationMiddleware(MutationMiddleware):
    """Middleware that makes mutations atomic."""

    # Priority should be high enough so that the transaction is always exited,
    # meaning no other middleware raises an error before this one is exited.
    # To be safe, make sure this this middleware runs last.
    priority: int = 1000

    def __init__(self, params: MutationMiddlewareParams) -> None:
        self.atomic: transaction.Atomic | None = None
        super().__init__(params)

    def before(self) -> Self:
        self.atomic = transaction.atomic()
        self.atomic.__enter__()  # noqa: PLC2801
        return self

    def after(self, value: QueryResult) -> None:
        if self.atomic is not None:
            self.atomic.__exit__(None, None, None)

    def exception(self, exc: Exception) -> None:
        if self.atomic is not None:
            self.atomic.__exit__(type(exc), exc, exc.__traceback__)


class MutationMiddlewareHandler:
    """
    Executes defined middlewares for a MutationType.

    All middleware have three possible steps:
    - a before step, which is run before the mutation
    - an after step, which is run after the mutation
    - an exception step, which is run if an exception is raised during the mutation

    The middleware with the highest priority (lowest number) has its before step run first
    and after or exception steps last.
    """

    def __init__(
        self,
        info: GQLInfo,
        input_data: JsonObject,
        mutation_type: type[MutationType],
        instance: models.Model | None = None,
        instances: list[models.Model] | None = None,
    ) -> None:
        self.middleware: list[MutationMiddleware] = []

        self.params = MutationMiddlewareParams(
            mutation_type=mutation_type,
            info=info,
            input_data=input_data,
            instance=instance,
            instances=instances,
        )

        sorted_middleware = sorted(mutation_type.__middleware__(), key=lambda m: (m.priority, m.__name__))

        for middleware in sorted_middleware:
            self.middleware.append(middleware(self.params))

    def wrap(self, func: Callable[P, QueryResult], /) -> Callable[P, QueryResult]:
        """Wraps a mutation function with the middleware."""

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> QueryResult:
            for middleware in self.middleware:
                middleware.before()

            try:
                value = func(*args, **kwargs)
            except Exception as exc:
                for middleware in reversed(self.middleware):
                    middleware.exception(exc)
                raise
            else:
                for middleware in reversed(self.middleware):
                    middleware.after(value)

            return value

        return wrapper
