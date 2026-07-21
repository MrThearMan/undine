from __future__ import annotations

import sys
from pathlib import Path

import pytest
from graphql import parse, print_ast

COMPAT_DIR = Path(__file__).resolve().parent / "compatibility"
SCHEMA_PATH = COMPAT_DIR / "schema.graphql"


@pytest.fixture(autouse=True)
def _add_compat_to_sys_path():
    compat_dir = str(COMPAT_DIR)
    sys.path.insert(0, compat_dir)
    try:
        yield
    finally:
        sys.path.remove(compat_dir)


def test_compatibility_products_schema_matches_tracked_file(undine_settings) -> None:
    """
    Smoke test: The products subgraph SDL that Undine renders must match the tracked `schema.graphql`.
    That schema has been evaluated to match Apollo's canonical products subgraph schema.
    This test detects drift between the two.

    If the there is drift, evaluate against the canonical schema.
    If the drift is ok, update the tracked file using `just export` in the compatibility directory.

    See: https://raw.githubusercontent.com/apollographql/apollo-federation-subgraph-compatibility/refs/heads/main/implementations/_template_library_/products.graphql
    """
    undine_settings.AUTOGENERATION = False
    from products.management.commands.export import render_schema  # type: ignore[import-not-found]  # noqa: PLC0415
    from products.schema import schema  # type: ignore[import-not-found]  # noqa: PLC0415

    undine_settings.SCHEMA = schema

    rendered = render_schema()
    tracked = SCHEMA_PATH.read_text()

    rendered_ast = parse(rendered)
    tracked_ast = parse(tracked)

    if rendered_ast.to_dict() != tracked_ast.to_dict():
        assert print_ast(rendered_ast) == print_ast(tracked_ast), "Compatibility subgraph SDL drift detected."
