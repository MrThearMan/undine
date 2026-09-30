from __future__ import annotations

import io
from inspect import cleandoc
from typing import TYPE_CHECKING

import pytest
from django.core.management import CommandError, call_command

from example_project.app.models import Task
from tests.helpers import exact
from undine import Entrypoint, Field, QueryType, RootType, create_schema
from undine.federation import KeyDirective, create_federation_schema
from undine.management.commands.print_schema import get_schema_sdl

if TYPE_CHECKING:
    from pathlib import Path

    from graphql import GraphQLSchema


def run_check_schema_changes(path: Path) -> str:
    out = io.StringIO()
    call_command("check_schema_changes", str(path), stdout=out)
    return out.getvalue().strip()


def create_example_schema() -> GraphQLSchema:
    class Query(RootType):
        @Entrypoint
        def name(self) -> str:
            return "foo"

        @Entrypoint
        def count(self, limit: int | None = None) -> int:
            return 1

    return create_schema(query=Query)


def test_check_schema_changes__no_changes(undine_settings, tmp_path) -> None:
    undine_settings.SCHEMA = create_example_schema()
    path = tmp_path / "schema.graphql"
    path.write_text(get_schema_sdl(), encoding="utf-8")

    output = run_check_schema_changes(path)

    assert output == f"No changes compared to schema file '{path}'."


def test_check_schema_changes__safe_changes(undine_settings, tmp_path) -> None:
    undine_settings.SCHEMA = create_example_schema()
    path = tmp_path / "schema.graphql"
    old_sdl = get_schema_sdl().replace("  count(\n    limit: Int = null\n  ): Int!\n", "")
    path.write_text(old_sdl, encoding="utf-8")

    output = run_check_schema_changes(path)

    assert output == cleandoc(
        """
        Safe changes:
          FIELD_ADDED: Field Query.count was added.
        """
    )


def test_check_schema_changes__dangerous_changes(undine_settings, tmp_path) -> None:
    undine_settings.SCHEMA = create_example_schema()
    path = tmp_path / "schema.graphql"
    old_sdl = get_schema_sdl().replace("limit: Int = null", "limit: Int = 10")
    path.write_text(old_sdl, encoding="utf-8")

    output = run_check_schema_changes(path)

    assert output == cleandoc(
        """
        Dangerous changes:
          ARG_DEFAULT_VALUE_CHANGE: Query.count(limit:) has changed defaultValue from 10 to null.
        """
    )


def test_check_schema_changes__breaking_changes(undine_settings, tmp_path) -> None:
    undine_settings.SCHEMA = create_example_schema()
    path = tmp_path / "schema.graphql"
    old_sdl = get_schema_sdl().replace("  name: String!\n", "  name: String!\n  removed: String\n")
    path.write_text(old_sdl, encoding="utf-8")

    out = io.StringIO()
    with pytest.raises(CommandError) as error:
        call_command("check_schema_changes", str(path), stdout=out)

    assert str(error.value) == f"Found 1 breaking change(s) compared to schema file '{path}'."
    assert out.getvalue().strip() == cleandoc(
        """
        Breaking changes:
          FIELD_REMOVED: Field Query.removed was removed.
        """
    )


def test_check_schema_changes__file_missing(undine_settings, tmp_path) -> None:
    undine_settings.SCHEMA = create_example_schema()
    path = tmp_path / "schema.graphql"

    msg = f"Schema file '{path}' does not exist. Create it with `python manage.py print_schema > {path}`."
    with pytest.raises(CommandError, match=exact(msg)):
        run_check_schema_changes(path)


def test_check_schema_changes__federation_schema(undine_settings, tmp_path) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)
    path = tmp_path / "schema.graphql"
    path.write_text(get_schema_sdl(), encoding="utf-8")

    output = run_check_schema_changes(path)

    assert output == f"No changes compared to schema file '{path}'."
