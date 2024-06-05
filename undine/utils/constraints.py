from __future__ import annotations

import re

from django.apps import apps
from django.db.models import CheckConstraint, UniqueConstraint

__all__ = [
    "get_constraint_message",
]


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
        constraint = match.group("constraint")
        return postgres_unique_constraint_message(constraint, message)

    if (match := CONSTRAINT_PATTERNS[2].match(message)) is not None:
        constraint = match.group("constraint")
        return sqlite_check_constraint_message(constraint, message)

    if (match := CONSTRAINT_PATTERNS[3].match(message)) is not None:
        fields: list[str] = match.group("fields").split(",")
        relation = fields[0].split(".")[0]
        fields = [field.strip().split(".")[1] for field in fields]
        return sqlite_unique_constraint_message(relation, fields, message)

    return message


def postgres_check_constraint_message(relation: str, constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        if model._meta.db_table != relation:
            continue
        for constr in model._meta.constraints:
            if not isinstance(constr, CheckConstraint):
                continue  # pragma: no cover
            if constr.name == constraint:
                return str(constr.violation_error_message)
    return default_message


def postgres_unique_constraint_message(constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        for constr in model._meta.constraints:
            if not isinstance(constr, UniqueConstraint):
                continue  # pragma: no cover
            if constr.name == constraint:
                return str(constr.violation_error_message)
    return default_message


def sqlite_check_constraint_message(constraint: str, default_message: str) -> str:
    for model in apps.get_models():
        for constr in model._meta.constraints:
            if not isinstance(constr, CheckConstraint):
                continue  # pragma: no cover
            if constr.name == constraint:
                return str(constr.violation_error_message)
    return default_message


def sqlite_unique_constraint_message(relation: str, fields: list[str], default_message: str) -> str:
    for model in apps.get_models():
        if model._meta.db_table != relation:
            continue
        for constr in model._meta.constraints:
            if not isinstance(constr, UniqueConstraint):
                continue  # pragma: no cover
            if set(constr.fields) == set(fields):
                return str(constr.violation_error_message)
    return default_message
