from __future__ import annotations

from contextlib import contextmanager

from django.db.models import CheckConstraint, Q, UniqueConstraint

from example_project.app.models import Task
from undine.utils.constraints import get_constraint_message


@contextmanager
def with_example_constraints() -> None:
    check_constraint = CheckConstraint(
        name="check_example",
        check=~Q(name__contains="example"),
        violation_error_message="Example constraint violation message.",
    )
    unique_constraint = UniqueConstraint(
        fields=["name", "type"],
        name="unique_name",
        violation_error_message="Example unique violation message.",
    )

    try:
        Task._meta.constraints.append(check_constraint)
        Task._meta.constraints.append(unique_constraint)
        yield
    finally:
        Task._meta.constraints.remove(check_constraint)
        Task._meta.constraints.remove(unique_constraint)


@with_example_constraints()
def test_get_constraint_message__check_postgres() -> None:
    msg = 'new row for relation "app_task" violates check constraint "check_example"'
    assert get_constraint_message(msg) == "Example constraint violation message."


@with_example_constraints()
def test_get_constraint_message__check_postgres__unknown_constraint() -> None:
    msg = 'new row for relation "app_task" violates check constraint "foo"'
    assert get_constraint_message(msg) == msg


@with_example_constraints()
def test_get_constraint_message__unique_postgres() -> None:
    msg = 'duplicate key value violates unique constraint "unique_name"'
    assert get_constraint_message(msg) == "Example unique violation message."


@with_example_constraints()
def test_get_constraint_message__unique_postgres__unknown_constraint() -> None:
    msg = 'duplicate key value violates unique constraint "foo"'
    assert get_constraint_message(msg) == msg


@with_example_constraints()
def test_get_constraint_message__check_sqlite() -> None:
    msg = "CHECK constraint failed: check_example"
    assert get_constraint_message(msg) == "Example constraint violation message."


@with_example_constraints()
def test_get_constraint_message__check_sqlite__unknown_constraint() -> None:
    msg = "CHECK constraint failed: foo"
    assert get_constraint_message(msg) == msg


@with_example_constraints()
def test_get_constraint_message__unique_sqlite() -> None:
    msg = "UNIQUE constraint failed: app_task.name, app_task.type"
    assert get_constraint_message(msg) == "Example unique violation message."


@with_example_constraints()
def test_get_constraint_message__unique_sqlite__unknown_fields() -> None:
    msg = "UNIQUE constraint failed: app_task.foo, app_task.bar"
    assert get_constraint_message(msg) == msg


@with_example_constraints()
def test_get_constraint_message__unknown_message() -> None:
    msg = "Unknown message."
    assert get_constraint_message(msg) == msg
