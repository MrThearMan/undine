from __future__ import annotations

import io
from inspect import cleandoc
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from example_project.app.models import Task
from undine import Entrypoint, Field, QueryType, RootType, create_schema
from undine.federation import KeyDirective, create_federation_schema
from undine.settings import example_schema
from undine.typing import DjangoRequestProtocol


def run_print_schema(*, check: str | bool = False) -> str:
    out = io.StringIO()
    if isinstance(check, str):
        call_command("print_schema", check=check, stdout=out)
    elif check:
        call_command("print_schema", "--check", stdout=out)
    else:
        call_command("print_schema", stdout=out)
    return out.getvalue().strip()


def test_print_schema(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    sdl = run_print_schema()

    assert sdl == cleandoc(
        """
        type Query {
          testing: String
        }
        """
    )


def test_print_schema__federation_schema(undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    sdl = run_print_schema()

    federation_sdl = undine_settings.SCHEMA.extensions[undine_settings.FEDERATION_SDL_EXTENSIONS_KEY].strip()

    assert sdl == federation_sdl

    # The federation machinery is not part of the subgraph SDL.
    assert "_Service" not in sdl
    assert "_Entity" not in sdl
    assert "extend schema @link" in sdl


def test_print_schema__visibility_does_not_affect_output(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @Field
        def hidden(self) -> str: ...

        @hidden.visible
        def hidden_visible(self, request: DjangoRequestProtocol) -> bool:
            return False

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    assert undine_settings.SCHEMA.extensions[undine_settings.VISIBILITY_ACTIVE_EXTENSIONS_KEY] is True

    sdl = run_print_schema()

    assert "hidden: String!" in sdl


def test_print_schema__check__up_to_date(undine_settings, tmp_path) -> None:
    undine_settings.SCHEMA = example_schema

    schema_file = tmp_path / "schema.graphql"
    schema_file.write_text(undine_settings.SDL_PRINTER.print_schema(example_schema), encoding="utf-8")

    sdl = run_print_schema(check=str(schema_file))

    assert "is up to date" in sdl


def test_print_schema__check__out_of_date(undine_settings, tmp_path) -> None:
    undine_settings.SCHEMA = example_schema

    schema_file = tmp_path / "schema.graphql"
    schema_file.write_text("type Query {\n  other: String\n}", encoding="utf-8")

    with pytest.raises(CommandError, match="is out of date"):
        run_print_schema(check=str(schema_file))


def test_print_schema__check__file_missing(undine_settings, tmp_path) -> None:
    undine_settings.SCHEMA = example_schema

    schema_file = tmp_path / "schema.graphql"

    with pytest.raises(CommandError, match="does not exist"):
        run_print_schema(check=str(schema_file))


def test_print_schema__check__default_path(undine_settings, tmp_path, monkeypatch) -> None:
    undine_settings.SCHEMA = example_schema

    monkeypatch.chdir(tmp_path)
    Path("schema.graphql").write_text(undine_settings.SDL_PRINTER.print_schema(example_schema), encoding="utf-8")

    sdl = run_print_schema(check=True)

    assert "'schema.graphql' is up to date" in sdl
