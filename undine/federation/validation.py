from __future__ import annotations

from typing import TYPE_CHECKING

from undine.exceptions import (
    DirectiveVersionError,
    FederationFieldSetTooComplexError,
    FederationKeyRequiresCustomResolverError,
    FederationMultipleKeysRequireCustomResolverError,
    FederationRequiresNonExternalFieldError,
    FederationRequiresUnknownFieldError,
    MissingFederationKeysError,
)
from undine.federation.federation_type import FEDERATION_TYPE_REGISTRY
from undine.federation.version import is_supported_in_federation_version
from undine.settings import undine_settings
from undine.utils.text import to_schema_name

if TYPE_CHECKING:
    from undine import Directive
    from undine.federation.directives import KeyDirective, RequiresDirective
    from undine.federation.federation_type import FederationField, FederationType
    from undine.query import QueryType


__all__ = [
    "validate_federation_field_requires",
    "validate_federation_type_key",
    "validate_federation_types_have_keys",
    "validate_query_type_key",
]


def validate_query_type_key(directive: KeyDirective, query_type: type[QueryType]) -> None:
    if "__resolve_reference__" in query_type.__dict__:
        return

    if directive.__parameters__["resolvable"]:
        validate_only_one_resolvable_key_directive(query_type)
        validate_simple_query_type_key(directive, query_type)


def validate_only_one_resolvable_key_directive(query_type: type[QueryType]) -> None:
    from undine.federation.directives import KeyDirective  # noqa: PLC0415

    resolvable_key_count = sum(
        1
        for other in query_type.__directives__
        if isinstance(other, KeyDirective) and other.__parameters__["resolvable"]
    )
    if resolvable_key_count != 1:
        raise FederationMultipleKeysRequireCustomResolverError(cls=query_type)


def validate_simple_query_type_key(directive: KeyDirective, query_type: type[QueryType]) -> None:
    fields = directive.__parameters__["fields"]

    if any(value in fields for value in ("{", ":", " ")):
        raise FederationFieldSetTooComplexError(fields=fields, cls=query_type)

    schema_name_to_field = {
        field.schema_name or to_schema_name(name): field for (name, field) in query_type.__field_map__.items()
    }

    for token in fields.split():
        field = schema_name_to_field.get(token)
        if field is None:
            raise FederationKeyRequiresCustomResolverError(fields=fields, cls=query_type, token=token)


def validate_federation_type_key(directive: KeyDirective, federation_type: type[FederationType]) -> None:
    if "__resolve_reference__" in federation_type.__dict__:
        return

    if directive.__parameters__["resolvable"]:
        validate_only_one_resolvable_key_directive_federation_type(federation_type)
        validate_simple_federation_type_key(directive, federation_type)


def validate_only_one_resolvable_key_directive_federation_type(federation_type: type[FederationType]) -> None:
    from undine.federation.directives import KeyDirective  # noqa: PLC0415

    resolvable_key_count = sum(
        1
        for other in federation_type.__directives__
        if isinstance(other, KeyDirective) and other.__parameters__["resolvable"]
    )
    if resolvable_key_count != 1:
        raise FederationMultipleKeysRequireCustomResolverError(cls=federation_type)


def validate_simple_federation_type_key(directive: KeyDirective, federation_type: type[FederationType]) -> None:
    fields = directive.__parameters__["fields"]

    if any(value in fields for value in ("{", ":", " ")):
        raise FederationFieldSetTooComplexError(fields=fields, cls=federation_type)

    schema_name_to_field = {
        field.schema_name or to_schema_name(name): field for (name, field) in federation_type.__field_map__.items()
    }

    for token in fields.split():
        field = schema_name_to_field.get(token)
        if field is None:
            raise FederationKeyRequiresCustomResolverError(fields=fields, cls=federation_type, token=token)


def validate_federation_field_requires(directive: RequiresDirective, field: FederationField) -> None:
    from undine.federation.directives import ExternalDirective  # noqa: PLC0415

    fields = directive.__parameters__["fields"]
    field_map = {
        field.schema_name or to_schema_name(name): field
        for (name, field) in field.federation_type.__field_map__.items()
    }

    for token in fields.split():
        target = field_map.get(token)
        if target is None:
            raise FederationRequiresUnknownFieldError(
                fields=fields,
                cls=field.federation_type,
                name=field.name,
                token=token,
            )

        if not any(isinstance(d, ExternalDirective) for d in target.directives):
            raise FederationRequiresNonExternalFieldError(
                fields=fields,
                cls=field.federation_type,
                name=field.name,
                token=token,
            )


def validate_federation_types_have_keys() -> None:
    from undine.federation.directives import KeyDirective  # noqa: PLC0415

    for federation_type in FEDERATION_TYPE_REGISTRY.values():
        has_key = any(isinstance(directive, KeyDirective) for directive in federation_type.__directives__)
        if not has_key:
            raise MissingFederationKeysError(cls=federation_type)


def validate_directive_min_version(cls: type[Directive]) -> None:
    min_version: str | None = cls.__extensions__.get(undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY)
    if min_version is None:
        return
    if not is_supported_in_federation_version(min_version):
        raise DirectiveVersionError(directive=cls.__schema_name__, min_version=min_version)
