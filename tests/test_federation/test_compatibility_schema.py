from __future__ import annotations

import sys
from pathlib import Path

import pytest
from graphql import parse, print_ast

from tests.test_federation.helpers import render_compatibility_schema, undefined_directive_usages

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
    rendered = render_compatibility_schema(undine_settings)
    tracked = SCHEMA_PATH.read_text()

    rendered_ast = parse(rendered)
    tracked_ast = parse(tracked)

    if rendered_ast.to_dict() != tracked_ast.to_dict():
        assert print_ast(rendered_ast) == print_ast(tracked_ast), "Compatibility subgraph SDL drift detected."


def test_compatibility_products_schema_defines_every_directive_it_uses(undine_settings) -> None:
    """
    The exported subgraph SDL must only use directives that it defines or imports through `@link`.
    A directive that the export filters out of the definitions but leaves in the field usages makes
    `rover supergraph compose` fail in the federation compatibility workflow.
    """
    rendered = render_compatibility_schema(undine_settings)
    document = parse(rendered)

    assert undefined_directive_usages(document) == set()
