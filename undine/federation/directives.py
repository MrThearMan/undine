from __future__ import annotations

from typing import Any, Literal, Self

from graphql import DirectiveLocation, GraphQLBoolean, GraphQLInt, GraphQLList, GraphQLNonNull, GraphQLString

from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveVersionError, FederationFeatureVersionError
from undine.federation.federation_type import FederationField, FederationTypeMeta
from undine.federation.scalars import (
    FederationContextFieldValue,
    FederationFieldSet,
    FederationLinkImport,
    FederationLinkPurpose,
    FederationPolicy,
    FederationScope,
)
from undine.federation.validation import (
    validate_directive_min_version,
    validate_federation_field_requires,
    validate_federation_type_key,
    validate_query_type_key,
)
from undine.federation.version import get_federation_spec_url, is_supported_in_federation_version
from undine.interface import InterfaceTypeMeta
from undine.query import QueryTypeMeta
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import DIRECTIVE_REGISTRY

__all__ = [
    "AuthenticatedDirective",
    "CacheTagDirective",
    "ComposeDirectiveDirective",
    "ContextDirective",
    "CostDirective",
    "ExternalDirective",
    "FromContextDirective",
    "InaccessibleDirective",
    "InterfaceObjectDirective",
    "KeyDirective",
    "LinkDirective",
    "ListSizeDirective",
    "OverrideDirective",
    "PolicyDirective",
    "ProvidesDirective",
    "RequiresDirective",
    "RequiresScopesDirective",
    "ShareableDirective",
    "TagDirective",
]


class LinkDirective(
    Directive,
    locations=[DirectiveLocation.SCHEMA],
    schema_name="link",
    is_repeatable=True,
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.0",
    },
):
    url = DirectiveArgument(GraphQLNonNull(GraphQLString))
    as_ = DirectiveArgument(GraphQLString, schema_name="as")
    import_ = DirectiveArgument(GraphQLList(FederationLinkImport), schema_name="import")
    for_ = DirectiveArgument(FederationLinkPurpose, schema_name="for")

    def __init__(
        self,
        *,
        url: str,
        as_: str | None = None,
        import_: list[str | dict[str, str]] | None = None,
        for_: Literal["SECURITY", "EXECUTION"] | None = None,
    ) -> None:
        super().__init__(url=url, as_=as_ or None, import_=import_ or None, for_=for_ or None)

    def __connected__(self, other: Any) -> None:
        cls = type(self)
        if cls.__schema_name__ not in DIRECTIVE_REGISTRY:
            DIRECTIVE_REGISTRY[cls.__schema_name__] = cls

    @classmethod
    def autogenerate(cls) -> Self:
        imports = sorted(f"@{directive.__schema_name__}" for directive in USED_FEDERATION_DIRECTIVES)
        return cls(url=get_federation_spec_url(), import_=imports)  # type: ignore[arg-type]


class KeyDirective(
    Directive,
    locations=[DirectiveLocation.OBJECT, DirectiveLocation.INTERFACE],
    schema_name="key",
    is_repeatable=True,
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.0",
    },
):
    fields = DirectiveArgument(
        GraphQLNonNull(FederationFieldSet),
        description="Selection set of fields that uniquely identify the entity.",
    )
    resolvable = DirectiveArgument(
        GraphQLNonNull(GraphQLBoolean),
        default_value=True,
        description="Whether this subgraph can resolve entities of this type.",
    )

    def __init__(self, *, fields: str, resolvable: bool = True) -> None:
        if not fields.strip():
            msg = "`fields` must be a non-empty FieldSet string."
            raise ValueError(msg)
        super().__init__(fields=fields, resolvable=resolvable)

    def __connected__(self, other: Any) -> None:
        cls = type(self)
        _register_federation_directive_used(cls)
        if isinstance(other, QueryTypeMeta):
            validate_query_type_key(self, other)  # type: ignore[arg-type]
        elif isinstance(other, FederationTypeMeta):
            validate_federation_type_key(self, other)  # type: ignore[arg-type]
        elif isinstance(other, InterfaceTypeMeta) and not is_supported_in_federation_version("2.3"):
            raise FederationFeatureVersionError(feature="@key on interfaces", min_version="2.3")


class ShareableDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION, DirectiveLocation.OBJECT],
    schema_name="shareable",
    is_repeatable=True,
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.0",
    },
):
    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class _ShareableIsRepeatable:
    """Descriptor exposing `@shareable`'s spec-correct repeatability for the current `FEDERATION_VERSION`."""

    def __get__(self, instance: Any, owner: type | None = None) -> bool:
        return is_supported_in_federation_version("2.2")


ShareableDirective.__is_repeatable__ = _ShareableIsRepeatable()  # type: ignore[assignment]


class ExternalDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION, DirectiveLocation.OBJECT],
    schema_name="external",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.0",
    },
):
    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class RequiresDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION],
    schema_name="requires",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.0",
    },
):
    fields = DirectiveArgument(
        GraphQLNonNull(FederationFieldSet),
        description="Selection set of fields from the parent entity that must be fetched by other subgraphs.",
    )

    def __init__(self, *, fields: str) -> None:
        if not fields.strip():
            msg = "`fields` must be a non-empty FieldSet string."
            raise ValueError(msg)
        super().__init__(fields=fields)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))
        if isinstance(other, FederationField):
            validate_federation_field_requires(self, other)


class ProvidesDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION],
    schema_name="provides",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.0",
    },
):
    fields = DirectiveArgument(
        GraphQLNonNull(FederationFieldSet),
        description="Selection set of fields that this subgraph can provide for the referenced entity.",
    )

    def __init__(self, *, fields: str) -> None:
        if not fields.strip():
            msg = "`fields` must be a non-empty FieldSet string."
            raise ValueError(msg)
        super().__init__(fields=fields)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class OverrideDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION],
    schema_name="override",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.0",
    },
):
    from_ = DirectiveArgument(
        GraphQLNonNull(GraphQLString),
        schema_name="from",
        description="Name of the subgraph that this subgraph is overriding.",
    )
    label = DirectiveArgument(
        GraphQLString,
        description="Progressive override label controlling the fraction of traffic routed to this subgraph.",
    )

    def __init__(self, *, from_: str, label: str | None = None) -> None:
        if label is not None and not is_supported_in_federation_version("2.7"):
            raise DirectiveVersionError(directive="override(label:)", min_version="2.7")
        super().__init__(from_=from_, label=label)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class InaccessibleDirective(
    Directive,
    locations=[
        DirectiveLocation.FIELD_DEFINITION,
        DirectiveLocation.OBJECT,
        DirectiveLocation.INTERFACE,
        DirectiveLocation.UNION,
        DirectiveLocation.ARGUMENT_DEFINITION,
        DirectiveLocation.SCALAR,
        DirectiveLocation.ENUM,
        DirectiveLocation.ENUM_VALUE,
        DirectiveLocation.INPUT_OBJECT,
        DirectiveLocation.INPUT_FIELD_DEFINITION,
    ],
    schema_name="inaccessible",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.0",
    },
):
    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class TagDirective(
    Directive,
    locations=[
        DirectiveLocation.FIELD_DEFINITION,
        DirectiveLocation.OBJECT,
        DirectiveLocation.INTERFACE,
        DirectiveLocation.UNION,
        DirectiveLocation.ARGUMENT_DEFINITION,
        DirectiveLocation.SCALAR,
        DirectiveLocation.ENUM,
        DirectiveLocation.ENUM_VALUE,
        DirectiveLocation.INPUT_OBJECT,
        DirectiveLocation.INPUT_FIELD_DEFINITION,
    ],
    schema_name="tag",
    is_repeatable=True,
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.0",
    },
):
    name = DirectiveArgument(
        GraphQLNonNull(GraphQLString),
        description="An arbitrary string tag applied to the schema element.",
    )

    def __init__(self, *, name: str) -> None:
        super().__init__(name=name)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class ComposeDirectiveDirective(
    Directive,
    locations=[DirectiveLocation.SCHEMA],
    schema_name="composeDirective",
    is_repeatable=True,
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.1",
    },
):
    name = DirectiveArgument(
        GraphQLNonNull(GraphQLString),
        description="Name of a custom directive to include in the supergraph schema.",
    )

    def __init__(self, *, name: str) -> None:
        super().__init__(name=name)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class InterfaceObjectDirective(
    Directive,
    locations=[DirectiveLocation.OBJECT],
    schema_name="interfaceObject",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.3",
    },
):
    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class AuthenticatedDirective(
    Directive,
    locations=[
        DirectiveLocation.FIELD_DEFINITION,
        DirectiveLocation.OBJECT,
        DirectiveLocation.INTERFACE,
        DirectiveLocation.SCALAR,
        DirectiveLocation.ENUM,
    ],
    schema_name="authenticated",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.5",
    },
):
    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class RequiresScopesDirective(
    Directive,
    locations=[
        DirectiveLocation.FIELD_DEFINITION,
        DirectiveLocation.OBJECT,
        DirectiveLocation.INTERFACE,
        DirectiveLocation.SCALAR,
        DirectiveLocation.ENUM,
    ],
    schema_name="requiresScopes",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.5",
    },
):
    scopes = DirectiveArgument(
        GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLList(GraphQLNonNull(FederationScope))))),
        description="Scopes required to access the annotated schema element.",
    )

    def __init__(self, *, scopes: list[list[str]]) -> None:
        super().__init__(scopes=scopes)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class PolicyDirective(
    Directive,
    locations=[
        DirectiveLocation.FIELD_DEFINITION,
        DirectiveLocation.OBJECT,
        DirectiveLocation.INTERFACE,
        DirectiveLocation.SCALAR,
        DirectiveLocation.ENUM,
    ],
    schema_name="policy",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.6",
    },
):
    policies = DirectiveArgument(
        GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLList(GraphQLNonNull(FederationPolicy))))),
        description="Policies required to access the annotated schema element.",
    )

    def __init__(self, *, policies: list[list[str]]) -> None:
        super().__init__(policies=policies)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class ContextDirective(
    Directive,
    locations=[
        DirectiveLocation.OBJECT,
        DirectiveLocation.INTERFACE,
        DirectiveLocation.UNION,
    ],
    schema_name="context",
    is_repeatable=True,
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.8",
    },
):
    name = DirectiveArgument(
        GraphQLNonNull(GraphQLString),
        description="Name identifying the context that the annotated type contributes to.",
    )

    def __init__(self, *, name: str) -> None:
        super().__init__(name=name)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class FromContextDirective(
    Directive,
    locations=[DirectiveLocation.ARGUMENT_DEFINITION],
    schema_name="fromContext",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.8",
    },
):
    field = DirectiveArgument(
        FederationContextFieldValue,
        description="Selection path resolving the argument's value from a named context.",
    )

    def __init__(self, *, field: str) -> None:
        super().__init__(field=field)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class CostDirective(
    Directive,
    locations=[
        DirectiveLocation.ARGUMENT_DEFINITION,
        DirectiveLocation.ENUM,
        DirectiveLocation.FIELD_DEFINITION,
        DirectiveLocation.INPUT_FIELD_DEFINITION,
        DirectiveLocation.OBJECT,
        DirectiveLocation.SCALAR,
    ],
    schema_name="cost",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.9",
    },
):
    weight = DirectiveArgument(
        GraphQLNonNull(GraphQLInt),
        description="Weight applied to the annotated schema element by the demand control cost model.",
    )

    def __init__(self, *, weight: int) -> None:
        super().__init__(weight=weight)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class ListSizeDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION],
    schema_name="listSize",
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.9",
    },
):
    assumed_size = DirectiveArgument(
        GraphQLInt,
        schema_name="assumedSize",
        description="Assumed maximum length used by the demand control cost model.",
    )
    slicing_arguments = DirectiveArgument(
        GraphQLList(GraphQLNonNull(GraphQLString)),
        schema_name="slicingArguments",
        description="Arguments that slice this list (e.g. `first`, `last`).",
    )
    sized_fields = DirectiveArgument(
        GraphQLList(GraphQLNonNull(GraphQLString)),
        schema_name="sizedFields",
        description="Subfields whose lengths are governed by the slicing arguments.",
    )
    require_one_slicing_argument = DirectiveArgument(
        GraphQLBoolean,
        schema_name="requireOneSlicingArgument",
        default_value=True,
        description="Whether at least one slicing argument must be supplied to bound the list.",
    )

    def __init__(
        self,
        *,
        assumed_size: int | None = None,
        slicing_arguments: list[str] | None = None,
        sized_fields: list[str] | None = None,
        require_one_slicing_argument: bool = True,
    ) -> None:
        super().__init__(
            assumed_size=assumed_size,
            slicing_arguments=slicing_arguments,
            sized_fields=sized_fields,
            require_one_slicing_argument=require_one_slicing_argument,
        )

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


class CacheTagDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION, DirectiveLocation.OBJECT],
    schema_name="cacheTag",
    is_repeatable=True,
    register=False,
    extensions={  # type: ignore[arg-type]
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True,
        undine_settings.FEDERATION_MIN_VERSION_EXTENSIONS_KEY: "2.12",
    },
):
    format = DirectiveArgument(
        GraphQLNonNull(GraphQLString),
        description="Template string used to derive cache tags for the annotated schema element.",
    )

    def __init__(self, *, format: str) -> None:  # noqa: A002
        super().__init__(format=format)

    def __connected__(self, other: Any) -> None:
        _register_federation_directive_used(type(self))


USED_FEDERATION_DIRECTIVES: set[type[Directive]] = set()
"""Federation directive classes that have been applied to a target somewhere in the schema."""


def _register_federation_directive_used(cls: type[Directive]) -> None:
    validate_directive_min_version(cls)
    USED_FEDERATION_DIRECTIVES.add(cls)
    if cls.__schema_name__ not in DIRECTIVE_REGISTRY:
        DIRECTIVE_REGISTRY[cls.__schema_name__] = cls
