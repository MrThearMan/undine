from __future__ import annotations

import io
from inspect import cleandoc

from django.core.management import call_command

from undine.management.commands import print_schema
from undine.settings import example_schema

COMMAND_NAME = print_schema.__name__.split(".")[-1]


def test_print_schema(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    out = io.StringIO()

    call_command(COMMAND_NAME, stdout=out)

    assert out.getvalue().strip() == cleandoc(
        """
        type Query {
          testing: String
        }
        """
    )
