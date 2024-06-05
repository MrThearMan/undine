from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Callable, get_type_hints

from graphql import Undefined

from undine.utils.model_utils import generic_relations_for_generic_foreign_key

if TYPE_CHECKING:
    from types import UnionType

    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.db.models import Model, OrderBy, Q

    from undine import QueryType
    from undine.parsers.parse_model_relation_info import RelationType
    from undine.typing import ExpressionLike, FilterRef, GenericField, RelatedField

__all__ = [
    "Calculated",
    "FilterResults",
    "GraphQLParams",
    "LazyLambdaQueryType",
    "LazyQueryType",
    "LazyQueryTypeUnion",
    "LookupRef",
    "OrderResults",
    "Parameter",
    "PostSaveData",
    "RelatedFieldInfo",
    "RootAndInfoParams",
    "TypeRef",
]


@dataclasses.dataclass(frozen=True, slots=True)
class Parameter:
    """Represents a parameter for a function."""

    name: str
    annotation: type | UnionType
    default_value: Any = Undefined
    docstring: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class FilterResults:
    """Holds the results of a QueryType filtering operation."""

    filters: list[Q]
    aliases: dict[str, ExpressionLike]
    distinct: bool
    none: bool = False


@dataclasses.dataclass(frozen=True, slots=True)
class OrderResults:
    """Holds the results of a QueryType ordering operation."""

    order_by: list[OrderBy]


@dataclasses.dataclass(frozen=True, slots=True)
class GraphQLParams:
    """Holds the parameters for a GraphQL request."""

    query: str
    variables: dict[str, Any] | None = None
    operation_name: str | None = None
    extensions: dict[str, Any] | None = None


@dataclasses.dataclass(slots=True)
class PostSaveData:
    """Holds the post-save handlers for the mutation handler."""

    post_save_handlers: list[Callable[[Model], Any]] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True, slots=True)
class TypeRef:
    """A reference to a type used by converters."""

    value: type | UnionType


@dataclasses.dataclass(frozen=True, slots=True)
class LookupRef:
    """A reference to a lookup expression used by converters."""

    ref: FilterRef
    lookup: str


@dataclasses.dataclass(frozen=True, slots=True)
class ValidatedPaginationArgs:
    """Pagination arguments that have been validated."""

    after: int | None
    before: int | None
    first: int | None
    last: int | None


@dataclasses.dataclass(frozen=True, slots=True)
class RootAndInfoParams:
    root_param: str | None
    info_param: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class LazyQueryType:
    """Represents a lazily evaluated QueryType for a related field."""

    field: RelatedField | GenericField

    def get_type(self) -> type[QueryType]:
        from undine.registies import QUERY_TYPE_REGISTRY  # noqa: PLC0415

        return QUERY_TYPE_REGISTRY[self.field.related_model]


@dataclasses.dataclass(frozen=True, slots=True)
class LazyLambdaQueryType:
    """Represents a lazily evaluated QueryType behind a lambda function."""

    callback: Callable[[], type[QueryType]]


@dataclasses.dataclass(frozen=True, slots=True)
class LazyQueryTypeUnion:
    """Represents a lazily evaluated QueryType for a related field."""

    field: GenericForeignKey

    def get_types(self) -> list[type[QueryType]]:
        from undine.registies import QUERY_TYPE_REGISTRY  # noqa: PLC0415

        return [
            QUERY_TYPE_REGISTRY[field.remote_field.related_model]
            for field in generic_relations_for_generic_foreign_key(self.field)
        ]


@dataclasses.dataclass(frozen=True, slots=True)
class RelatedFieldInfo:
    """Holds information about a related field on a model."""

    field_name: str
    related_name: str | None
    relation_type: RelationType
    nullable: bool
    related_model_pk_type: type | None
    model: type[Model] | None


@dataclasses.dataclass(frozen=True, slots=True)
class Calculated:
    """A QueryType Field wrapper for fields that need to be calculated using user input."""

    ref: Any
    """
    Any object that has an `__annotations__` attribute (e.g. TypedDict).
    Parsed to parameters.
    """

    parameters: list[Parameter] = dataclasses.field(init=False, default_factory=list)
    """
    Parameters parsed from the reference.
    Used as arguments for the field and can be used in the calculation.
    """

    return_annotation: type | UnionType = dataclasses.field(init=True, kw_only=True)
    """
    The return annotation of the reference.
    """

    def __post_init__(self) -> None:
        """Parse parameters from the given reference."""
        from undine.parsers import parse_class_variable_docstrings  # noqa: PLC0415

        type_hints = get_type_hints(self.ref)
        docstrings = parse_class_variable_docstrings(self.ref)

        defaults: dict[str, Any] = {}

        # NamedTuples have a `_field_defaults` attribute.
        if hasattr(self.ref, "_field_defaults"):
            defaults = self.ref._field_defaults

        elif dataclasses.is_dataclass(self.ref):
            for field in dataclasses.fields(self.ref):
                if field.default is not dataclasses.MISSING:
                    defaults[field.name] = field.default
                elif field.default_factory is not dataclasses.MISSING:
                    defaults[field.name] = field.default_factory()

        self.parameters.extend(
            Parameter(
                name=name,
                annotation=annotation,
                default_value=defaults.get(name, Undefined),
                docstring=docstrings.get(name),
            )
            for name, annotation in type_hints.items()
        )
