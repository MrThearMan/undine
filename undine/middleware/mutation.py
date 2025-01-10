from __future__ import annotations

from copy import deepcopy
from functools import wraps
from types import FunctionType
from typing import TYPE_CHECKING, Any, ParamSpec, Self

from django.db.transaction import Atomic, atomic
from django.db.utils import IntegrityError
from graphql import Undefined

from undine.errors.constraints import get_constraint_message
from undine.errors.exceptions import GraphQLModelConstaintViolationError
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.db.models import Model

    from undine import MutationType
    from undine.typing import GQLInfo, JsonObject, MutationKind, MutationResult

__all__ = [
    "AfterMutationMiddleware",
    "AtomicMutationMiddleware",
    "InputDataModificationMiddleware",
    "InputDataValidationMiddleware",
    "InputOnlyDataRemovalMiddleware",
    "IntegrityErrorHandlingMiddleware",
    "MutationMiddleware",
    "MutationMiddlewareHandler",
    "MutationPermissionCheckMiddleware",
]


P = ParamSpec("P")


class MutationMiddleware:
    """
    Base class for mutation middleware.

    MutationMiddlewares are run in the Entrypoint MutationType resolver,
    so they should handle the entire mutation.
    """

    priority: int
    """Middleware priority. Lower number means middleware context is entered earlier in the middleware stack."""

    supported_mutations: tuple[type[MutationKind], ...] = ("create", "update", "delete", "custom")  # TODO: Test
    """List of mutation kinds that this middleware supports."""

    def __init__(
        self,
        *,
        input_data: JsonObject,
        info: GQLInfo,
        mutation_type: type[MutationType],
        many: bool = False,
        instance: Model | None = None,
        instances: list[Model] | None = None,
    ) -> None:
        """
        Initialize the middleware.

        :param input_data: The input data for the mutation.
        :param info: The GraphQL resolve info for the request.
        :param mutation_type: The MutationType that is being executed.
        :param many: Whether the mutation is a bulk mutation.
        :param instance: The instance being mutated.
        :param instances: The list of instances being mutated.
        """
        self.input_data = input_data
        self.root_info = info
        self.mutation_type = mutation_type
        self.many = many
        self.instance = instance
        self.instances = instances

    def before(self) -> None:
        """Stuff that happens before the mutation is executed."""

    def after(self, value: MutationResult) -> None:
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

    supported_mutations: tuple[type[MutationKind], ...] = ("create", "update", "custom")

    def before(self) -> None:
        self.fill_input_data(self.mutation_type, self.input_data)

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
                input_data[field_name] = value = inpt.ref(inpt, self.root_info, *args)

            # Don't add default values from nested MutationTypes if no other data for it is provided.
            if value is Undefined:
                continue

            if is_subclass(inpt.ref, MutationType):
                self.fill_input_data(mutation_type=inpt.ref, input_data=value)


class MutationPermissionCheckMiddleware(MutationMiddleware):
    """
    Mutation middleware required for permission checks to work.

    Runs permission checks for all inputs and mutation types based on the given input data.
    For mutations on exiting instance(s), the instance is only included in the permissions check
    for the Entrypoint MutationType.
    """

    priority: int = 100

    def before(self) -> None:
        if self.many:
            self.check_perms_many(
                mutation_type=self.mutation_type,
                input_data=self.input_data,
                instances=self.instances,
            )
        else:
            self.check_perms_single(
                mutation_type=self.mutation_type,
                input_data=self.input_data,
                instance=self.instance,
            )

    def check_perms_single(
        self,
        mutation_type: type[MutationType],
        input_data: JsonObject,
        instance: Model | None = None,
    ) -> None:
        from undine import MutationType  # noqa: PLC0415

        # Check permissions for all fields individually.
        for field_name, value in input_data.items():
            inpt = mutation_type.__input_map__[field_name]

            if inpt.permissions_func is not None:
                inpt.permissions_func(inpt, self.root_info, value)

            if is_subclass(inpt.ref, MutationType):
                if inpt.many:
                    self.check_perms_many(inpt.ref, value)
                else:
                    self.check_perms_single(inpt.ref, value)

        # Check permissions for the MutationType.
        mutation_type.__permissions__(
            info=self.root_info,
            input_data=input_data,
            instance=instance,
        )

    def check_perms_many(
        self,
        mutation_type: type[MutationType],
        input_data: list[dict[str, Any]],
        instances: list[Model] | None = None,
    ) -> None:
        instances_by_pk = {inst.pk: inst for inst in instances or []}

        for item in input_data:
            instance = instances_by_pk.get(item.get("pk"))
            self.check_perms_single(mutation_type=mutation_type, input_data=item, instance=instance)


class InputDataValidationMiddleware(MutationMiddleware):
    """
    Mutation middleware required for input validation to work.

    Run validation for all fields in the given input data.
    """

    priority: int = 200

    def before(self) -> None:
        self.validate_data(self.mutation_type, self.input_data)

    def validate_data(self, mutation_type: type[MutationType], input_data: JsonObject) -> None:
        from undine import MutationType  # noqa: PLC0415

        if isinstance(input_data, list):
            for item in input_data:
                self.validate_data(mutation_type=mutation_type, input_data=item)
            return

        # Validate all fields individually.
        for field_name, value in input_data.items():
            inpt = mutation_type.__input_map__[field_name]

            if inpt.validator_func is not None:
                inpt.validator_func(inpt, self.root_info, value)

            if is_subclass(inpt.ref, MutationType):
                self.validate_data(mutation_type=inpt.ref, input_data=value)

        # Validate all fields together.
        mutation_type.__validate__(info=self.root_info, input_data=input_data)


class AfterMutationMiddleware(MutationMiddleware):
    """
    Mutation middleware required for after-mutation handling to work.

    Runs `__after__` method for the Entrypoint MutationType.
    """

    priority: int = 200

    def after(self, value: MutationResult) -> None:
        self.mutation_type.__after__(info=self.root_info, value=value)


class InputOnlyDataRemovalMiddleware(MutationMiddleware):
    """
    Mutation middleware required for input-only fields to work.

    Remove any input-only fields from the given input data.
    Add them back in after the mutation is executed.
    """

    priority: int = 300

    def __init__(self, **kwargs: Any) -> None:
        self.original_input_data = deepcopy(kwargs["input_data"])
        super().__init__(**kwargs)

    def before(self) -> None:
        self.remove_input_only_fields(self.mutation_type, self.input_data)

    def after(self, value: MutationResult) -> None:
        self.input_data = self.original_input_data

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

    # Priority should be high enough so that the transaction is always closed,
    # meaning no other middleware raises an error before `after` or `exception` is called.
    # To be safe, make sure this middleware runs last.
    priority: int = 1000

    def __init__(self, **kwargs: Any) -> None:
        self.atomic: Atomic | None = None
        super().__init__(**kwargs)

    def before(self) -> Self:
        self.atomic = atomic()
        self.atomic.__enter__()  # noqa: PLC2801
        return self

    def after(self, value: MutationResult) -> None:
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
    - an after step, which is run after the mutation (if successful)
    - an exception step, which is run if an exception is raised during the mutation

    The middleware with the highest priority (lowest number) has its before step run first
    and after or exception steps last.
    """

    def __init__(
        self,
        info: GQLInfo,
        input_data: JsonObject,
        mutation_type: type[MutationType],
        *,
        many: bool = False,
        instance: Model | None = None,
        instances: list[Model] | None = None,
    ) -> None:
        """
        Initialize the middleware handler.

        :param info: The GraphQL resolve info for the request.
        :param input_data: The input data for the mutation.
        :param mutation_type: The MutationType that is being executed.
        :param many: Whether the mutation is a bulk mutation.
        :param instance: The instance being mutated.
        :param instances: The list of instances being mutated.
        """
        self.middleware: list[MutationMiddleware] = [
            middleware(
                input_data=input_data,
                info=info,
                mutation_type=mutation_type,
                many=many,
                instance=instance,
                instances=instances,
            )
            for middleware in sorted(mutation_type.__middleware__(), key=lambda m: (m.priority, m.__name__))
            if mutation_type.__mutation_kind__ in middleware.supported_mutations
        ]

    def wrap(self, func: Callable[P, MutationResult], /) -> Callable[P, MutationResult]:
        """Wraps a mutation function with the middleware."""

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> MutationResult:
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
