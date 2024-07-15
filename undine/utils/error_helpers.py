from __future__ import annotations

import re
from contextlib import contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, ParamSpec, TypeVar

from django.apps import apps
from django.db import IntegrityError, models

from undine import error_codes
from undine.errors import GraphQLConversionError, GraphQLStatusError
from undine.utils.text import dotpath

if TYPE_CHECKING:
    from undine.typing import TModel

P = ParamSpec("P")
R = TypeVar("R")


def handle_conversion_errors(string: str):  # noqa: ANN201
    def decorator(func: Callable[P, R], **kwargs: Any) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(*args, **kwargs)
            except GraphQLConversionError:
                raise
            except Exception as error:
                raise GraphQLConversionError(string, args[0], extra=str(error)) from error

        return wrapper

    return decorator


CONSTRAINT_PATTERNS: tuple[re.Pattern, ...] = (
    # Postgres
    re.compile(r'^new row for relation "(?P<relation>\w+)" violates check constraint "(?P<constraint>\w+)"'),
    re.compile(r'^duplicate key value violates unique constraint "(?P<constraint>\w+)"'),
    # SQLite
    re.compile(r"^CHECK constraint failed: (?P<constraint>\w+)$"),
    re.compile(r"^UNIQUE constraint failed: (?P<fields>[\w., ]+)$"),
)


def get_constraint_message(message: str) -> str:
    """Try to get the error message for a constraint violation from the model meta constraints."""
    if (match := CONSTRAINT_PATTERNS[0].match(message)) is not None:
        relation: str = match.group("relation")
        constraint: str = match.group("constraint")
        return postgres_check_constraint_message(relation, constraint, message)

    if (match := CONSTRAINT_PATTERNS[1].match(message)) is not None:
        constraint: str = match.group("constraint")
        return postgres_unique_constraint_message(constraint, message)

    if (match := CONSTRAINT_PATTERNS[2].match(message)) is not None:
        constraint: str = match.group("constraint")
        return sqlite_check_constraint_message(constraint, message)

    if (match := CONSTRAINT_PATTERNS[3].match(message)) is not None:
        fields: list[str] = match.group("fields").split(",")
        relation: str = fields[0].split(".")[0]
        fields = [field.strip().split(".")[1] for field in fields]
        return sqlite_unique_constraint_message(relation, fields, message)

    return message


def postgres_check_constraint_message(relation: str, constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        if model._meta.db_table != relation:
            continue
        for constr in model._meta.constraints:
            if not isinstance(constr, models.CheckConstraint):
                continue  # pragma: no cover
            if constr.name == constraint:
                return constr.violation_error_message
    return default_message


def postgres_unique_constraint_message(constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        for constr in model._meta.constraints:
            if not isinstance(constr, models.UniqueConstraint):
                continue  # pragma: no cover
            if constr.name == constraint:
                return constr.violation_error_message
    return default_message


def sqlite_check_constraint_message(constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        for constr in model._meta.constraints:
            if not isinstance(constr, models.CheckConstraint):
                continue  # pragma: no cover
            if constr.name == constraint:
                return constr.violation_error_message
    return default_message


def sqlite_unique_constraint_message(relation: str, fields: list[str], default_message: str) -> str:
    for model in apps.get_models():
        if model._meta.db_table != relation:
            continue
        for constr in model._meta.constraints:
            if not isinstance(constr, models.UniqueConstraint):
                continue  # pragma: no cover
            if set(constr.fields) == set(fields):
                return constr.violation_error_message
    return default_message


@contextmanager
def handle_integrity_errors() -> None:
    """If an integrity error occurs, raise a GraphQLStatusError with the appropriate error code."""
    try:
        yield
    except IntegrityError as error:
        msg = get_constraint_message(error.args[0])
        raise GraphQLStatusError(msg, status=400, code=error_codes.MODEL_UNIQUE_CONSTRAINT_VIOLATION) from error


def get_instance_or_raise(model: type[TModel], key: str, value: Any) -> TModel:
    """
    Get model by the given key with the given value.
    Raise GraphQL errors appropriately if instace not found or multiple instances found.
    """
    try:
        return model._default_manager.get(**{key: value})

    except model.DoesNotExist as error:
        msg = f"`Lookup `{key}={value!r}` on model `{dotpath(model)}` did not match any row."
        raise GraphQLStatusError(msg, status=404, code=error_codes.MODEL_NOT_FOUND) from error

    except model.MultipleObjectsReturned as error:
        msg = f"`Lookup `{key}={value!r}` on model `{dotpath(model)}` matched more than one row."
        raise GraphQLStatusError(msg, status=500, code=error_codes.MODEL_MULTIPLE_OBJECTS) from error
