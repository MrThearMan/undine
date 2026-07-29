from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from graphql import TypeMetaFieldDef

from pytest_undine.client import GraphQLClientHTTPResponse
from undine.utils.graphql.introspection import (
    directive_introspection_type,
    field_introspection_type,
    get_directive_fields,
    get_field_fields,
    get_schema_fields,
    get_type_fields,
    resolve_type_meta_field_def,
    schema_introspection_type,
    type_introspection_type,
)


@contextmanager
def enable_visibility_patch():
    """Mirror `undine.utils.graphql.introspection.patch_introspection_schema`."""
    type_meta_field_def_resolver = TypeMetaFieldDef.resolve
    schema_fields = schema_introspection_type._fields
    directive_fields = directive_introspection_type._fields
    type_fields = type_introspection_type._fields
    field_fields = field_introspection_type._fields

    TypeMetaFieldDef.resolve = resolve_type_meta_field_def
    schema_introspection_type._fields = get_schema_fields
    directive_introspection_type._fields = get_directive_fields
    type_introspection_type._fields = get_type_fields
    field_introspection_type._fields = get_field_fields

    _re_evaluate_introspection_type_fields()

    try:
        yield
    finally:
        TypeMetaFieldDef.resolve = type_meta_field_def_resolver
        schema_introspection_type._fields = schema_fields
        directive_introspection_type._fields = directive_fields
        type_introspection_type._fields = type_fields
        field_introspection_type._fields = field_fields

        _re_evaluate_introspection_type_fields()


def _re_evaluate_introspection_type_fields():
    if "fields" in schema_introspection_type.__dict__:
        del schema_introspection_type.__dict__["fields"]

    if "fields" in directive_introspection_type.__dict__:
        del directive_introspection_type.__dict__["fields"]

    if "fields" in type_introspection_type.__dict__:
        del type_introspection_type.__dict__["fields"]

    if "fields" in field_introspection_type.__dict__:
        del field_introspection_type.__dict__["fields"]


def get_directives(response: GraphQLClientHTTPResponse) -> dict[str, dict[str, Any]]:
    schema = response.data["__schema"]
    return {directive["name"]: directive for directive in schema["directives"]}


def get_types(response: GraphQLClientHTTPResponse) -> dict[str, dict[str, Any]]:
    schema = response.data["__schema"]
    return {directive["name"]: directive for directive in schema["types"]}
