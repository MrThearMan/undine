from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from importlib import import_module
from types import FunctionType
from typing import Any, get_args

from django.db import models
from django.db.models import TextChoices
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute
from graphql import (
    GraphQLBoolean,
    GraphQLError,
    GraphQLField,
    GraphQLFloat,
    GraphQLInputField,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLString,
    GraphQLType,
    GraphQLUnionType,
)

from undine.dataclasses import LookupRef, TypeRef
from undine.scalars import (
    GraphQLAny,
    GraphQLBase64,
    GraphQLDate,
    GraphQLDateTime,
    GraphQLDecimal,
    GraphQLDuration,
    GraphQLEmail,
    GraphQLFile,
    GraphQLImage,
    GraphQLJSON,
    GraphQLTime,
    GraphQLURL,
    GraphQLUUID,
)
from undine.settings import undine_settings
from undine.typing import CombinableExpression, GQLInfo, TypedDictType, eval_type
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.graphql import get_or_create_graphql_enum, get_or_create_input_object_type, get_or_create_object_type
from undine.utils.lazy import LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion
from undine.utils.model_fields import TextChoicesField
from undine.utils.model_utils import generic_relations_for_generic_foreign_key, get_model_field
from undine.utils.text import dotpath, get_docstring, to_pascal_case

__all__ = [
    "convert_to_graphql_type",
]


convert_to_graphql_type = FunctionDispatcher[Any, GraphQLType](union_default=type)
"""
Convert a given value to a GraphQL input type or output type.

Positional arguments:
 - ref: The reference to convert.

Keyword arguments:
 - model: The model to use for the type.
 - is_input: (Optional) Whether the type is for an input or output. Defaults to `False`.
"""


# --- Python types -------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: str | type[str], **kwargs: Any) -> GraphQLType:
    if ref is str:
        return GraphQLString

    model_field = get_model_field(model=kwargs["model"], lookup=ref)
    return convert_to_graphql_type(model_field, **kwargs)


@convert_to_graphql_type.register
def _(_: type[bool], **kwargs: Any) -> GraphQLType:
    return GraphQLBoolean


@convert_to_graphql_type.register
def _(_: type[int], **kwargs: Any) -> GraphQLType:
    return GraphQLInt


@convert_to_graphql_type.register
def _(_: type[float], **kwargs: Any) -> GraphQLType:
    return GraphQLFloat


@convert_to_graphql_type.register
def _(_: type[Decimal], **kwargs: Any) -> GraphQLType:
    return GraphQLDecimal


@convert_to_graphql_type.register
def _(_: type[datetime.datetime], **kwargs: Any) -> GraphQLType:
    return GraphQLDateTime


@convert_to_graphql_type.register
def _(_: type[datetime.date], **kwargs: Any) -> GraphQLType:
    return GraphQLDate


@convert_to_graphql_type.register
def _(_: type[datetime.time], **kwargs: Any) -> GraphQLType:
    return GraphQLTime


@convert_to_graphql_type.register
def _(_: type[datetime.timedelta], **kwargs: Any) -> GraphQLType:
    return GraphQLDuration


@convert_to_graphql_type.register
def _(_: type[uuid.UUID], **kwargs: Any) -> GraphQLType:
    return GraphQLUUID


@convert_to_graphql_type.register
def _(ref: type[Enum], **kwargs: Any) -> GraphQLType:
    return get_or_create_graphql_enum(
        name=ref.__name__,
        values={name: value.value for name, value in ref.__members__.items()},
        description=get_docstring(ref),
    )


@convert_to_graphql_type.register
def _(ref: type[TextChoices], **kwargs: Any) -> GraphQLType:
    return get_or_create_graphql_enum(
        name=ref.__name__,
        values=dict(ref.choices),
        description=get_docstring(ref),
    )


@convert_to_graphql_type.register
def _(_: type, **kwargs: Any) -> GraphQLType:
    return GraphQLAny


@convert_to_graphql_type.register
def _(ref: type[list], **kwargs: Any) -> GraphQLType:
    args = get_args(ref)
    # For lists without type, or with a union type, default to any.
    if len(args) != 1:
        return GraphQLList(GraphQLAny)

    graphql_type, nullable = convert_to_graphql_type(args[0], return_nullable=True, **kwargs)
    if not nullable:
        graphql_type = GraphQLNonNull(graphql_type)
    return GraphQLList(graphql_type)


@convert_to_graphql_type.register
def _(ref: type[dict], **kwargs: Any) -> GraphQLType:
    if type(ref) is not TypedDictType:
        return GraphQLJSON

    ref: TypedDictType
    module_globals = vars(import_module(ref.__module__))
    is_input = kwargs.get("is_input", False)

    fields: dict[str, GraphQLField | GraphQLInputField] = {}
    for key, value in ref.__annotations__.items():
        evaluated_type = eval_type(value, globals_=module_globals)
        graphql_type, nullable = convert_to_graphql_type(evaluated_type, return_nullable=True, **kwargs)
        if not nullable:
            graphql_type = GraphQLNonNull(graphql_type)

        if is_input:
            fields[key] = GraphQLInputField(graphql_type)
        else:
            fields[key] = GraphQLField(graphql_type)

    description = get_docstring(ref)

    if is_input:
        return get_or_create_input_object_type(
            name=ref.__name__,
            fields=fields,
            description=description,
        )

    return get_or_create_object_type(
        name=ref.__name__,
        fields=fields,
        description=description,
    )


# --- Model fields -------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: models.CharField, **kwargs: Any) -> GraphQLType:
    if ref.choices is None:
        return GraphQLString

    # Generate a name for an enum based on the field it is used in.
    # This is required, since CharField doesn't know the name of the enum it is used in.
    # Use `TextChoicesField` instead to get more consistent naming.
    name = ref.model.__name__ + to_pascal_case(ref.name) + "Choices"

    return get_or_create_graphql_enum(
        name=name,
        values=dict(ref.choices),
        description=getattr(ref, "help_text", None) or None,
    )


@convert_to_graphql_type.register
def _(_: models.TextField, **kwargs: Any) -> GraphQLType:
    return GraphQLString


@convert_to_graphql_type.register
def _(ref: TextChoicesField, **kwargs: Any) -> GraphQLType:
    return get_or_create_graphql_enum(
        name=ref.choices_enum.__name__,
        values=dict(ref.choices),
        description=getattr(ref, "help_text", None) or get_docstring(ref.choices_enum),
    )


@convert_to_graphql_type.register
def _(_: models.BooleanField, **kwargs: Any) -> GraphQLType:
    return GraphQLBoolean


@convert_to_graphql_type.register
def _(_: models.IntegerField, **kwargs: Any) -> GraphQLType:
    return GraphQLInt


@convert_to_graphql_type.register
def _(_: models.FloatField, **kwargs: Any) -> GraphQLType:
    return GraphQLFloat


@convert_to_graphql_type.register
def _(_: models.DecimalField, **kwargs: Any) -> GraphQLType:
    return GraphQLDecimal


@convert_to_graphql_type.register
def _(_: models.DateField, **kwargs: Any) -> GraphQLType:
    return GraphQLDate


@convert_to_graphql_type.register
def _(_: models.DateTimeField, **kwargs: Any) -> GraphQLType:
    return GraphQLDateTime


@convert_to_graphql_type.register
def _(_: models.TimeField, **kwargs: Any) -> GraphQLType:
    return GraphQLTime


@convert_to_graphql_type.register
def _(_: models.DurationField, **kwargs: Any) -> GraphQLType:
    return GraphQLDuration


@convert_to_graphql_type.register
def _(_: models.UUIDField, **kwargs: Any) -> GraphQLType:
    return GraphQLUUID


@convert_to_graphql_type.register
def _(_: models.EmailField, **kwargs: Any) -> GraphQLType:
    return GraphQLEmail


@convert_to_graphql_type.register
def _(_: models.URLField, **kwargs: Any) -> GraphQLType:
    return GraphQLURL


@convert_to_graphql_type.register
def _(_: models.BinaryField, **kwargs: Any) -> GraphQLType:
    return GraphQLBase64


@convert_to_graphql_type.register
def _(_: models.JSONField, **kwargs: Any) -> GraphQLType:
    return GraphQLJSON


@convert_to_graphql_type.register
def _(_: models.FileField, **kwargs: Any) -> GraphQLType:
    return GraphQLFile


@convert_to_graphql_type.register
def _(_: models.ImageField, **kwargs: Any) -> GraphQLType:
    return GraphQLImage


@convert_to_graphql_type.register
def _(ref: models.OneToOneField, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.target_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: models.ForeignKey, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.target_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: models.ManyToManyField, **kwargs: Any) -> GraphQLType:
    type_ = convert_to_graphql_type(ref.target_field, **kwargs)
    return GraphQLList(GraphQLNonNull(type_))


@convert_to_graphql_type.register
def _(ref: models.OneToOneRel, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.target_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: models.ManyToOneRel, **kwargs: Any) -> GraphQLType:
    type_ = convert_to_graphql_type(ref.target_field, **kwargs)
    return GraphQLList(GraphQLNonNull(type_))


@convert_to_graphql_type.register
def _(ref: models.ManyToManyRel, **kwargs: Any) -> GraphQLType:
    type_ = convert_to_graphql_type(ref.target_field, **kwargs)
    return GraphQLList(GraphQLNonNull(type_))


# --- Django ORM ---------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: models.F, **kwargs: Any) -> GraphQLType:
    model: type[models.Model] = kwargs["model"]
    model_field = get_model_field(model=model, lookup=ref.name)
    return convert_to_graphql_type(model_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: CombinableExpression, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.output_field, **kwargs)


@convert_to_graphql_type.register
def _(_: models.Q, **kwargs: Any) -> GraphQLType:
    return GraphQLBoolean


@convert_to_graphql_type.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.field, **kwargs)


@convert_to_graphql_type.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.rel, **kwargs)


@convert_to_graphql_type.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.related, **kwargs)


@convert_to_graphql_type.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.rel if ref.reverse else ref.field, **kwargs)


# --- GraphQL types ------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: GraphQLType, **kwargs: Any) -> GraphQLType:
    return ref


# --- Custom types -------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: LazyQueryType, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.get_type(), **kwargs)


@convert_to_graphql_type.register
def _(ref: LazyQueryTypeUnion, **kwargs: Any) -> GraphQLUnionType:
    def resolve_type(obj: type[models.Model], info: GQLInfo, union_type: GraphQLUnionType) -> Any:
        nonlocal type_map

        object_type = type_map.get(obj.__class__)
        if object_type is None:
            msg = f"Union '{name}' doesn't contain a 'GraphQLObjectType' for model '{dotpath(obj.__class__)}'."
            raise GraphQLError(msg)

        return object_type.name

    name = ref.field.model.__name__ + to_pascal_case(ref.field.name)
    type_map = {model_type.__model__: convert_to_graphql_type(model_type, **kwargs) for model_type in ref.get_types()}

    return GraphQLUnionType(
        name=name,
        types=list(type_map.values()),
        resolve_type=resolve_type,  # type: ignore[arg-type]
    )


@convert_to_graphql_type.register
def _(ref: LazyLambdaQueryType, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.callback(), **kwargs)


@convert_to_graphql_type.register
def _(ref: TypeRef, **kwargs: Any) -> GraphQLType:
    return convert_to_graphql_type(ref.value, **kwargs)


# --- Deferred -----------------------------------------------------------------------------------------------------


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation

    from undine import MutationType, QueryType
    from undine.converters import convert_lookup_to_graphql_type, convert_to_python_type
    from undine.parsers import parse_first_param_type, parse_return_annotation
    from undine.relay import Connection, Node, PageInfoType

    @convert_to_graphql_type.register
    def _(ref: FunctionType, **kwargs: Any) -> GraphQLType:
        is_input = kwargs.get("is_input", False)
        annotation = parse_first_param_type(ref) if is_input else parse_return_annotation(ref)
        return convert_to_graphql_type(annotation, **kwargs)

    @convert_to_graphql_type.register
    def _(ref: LookupRef, **kwargs: Any) -> GraphQLType:
        kwargs["default_type"] = convert_to_python_type(ref.ref, **kwargs)
        return convert_lookup_to_graphql_type(ref.lookup, **kwargs)

    @convert_to_graphql_type.register
    def _(ref: GenericForeignKey, **kwargs: Any) -> GraphQLType:
        field = ref.model._meta.get_field(ref.fk_field)
        graphql_type = convert_to_graphql_type(field)

        if not kwargs.get("is_input", False):
            return graphql_type  # TODO: Test if correct

        name = ref.model.__name__ + to_pascal_case(ref.name)

        typename_enum = get_or_create_graphql_enum(
            name=f"{name}Choices",
            values={
                field.model.__name__.upper(): field.model.__name__
                for field in generic_relations_for_generic_foreign_key(ref)
            },
        )

        return get_or_create_input_object_type(
            name=f"{name}Input",
            fields={
                "typename": GraphQLInputField(GraphQLNonNull(typename_enum)),
                "pk": GraphQLInputField(GraphQLNonNull(graphql_type)),
            },
        )

    @convert_to_graphql_type.register
    def _(ref: GenericRelation, **kwargs: Any) -> GraphQLType:
        object_id_field = ref.related_model._meta.get_field(ref.object_id_field_name)
        type_ = convert_to_graphql_type(object_id_field, **kwargs)
        return GraphQLList(type_)

    @convert_to_graphql_type.register
    def _(ref: GenericRel, **kwargs: Any) -> GraphQLType:
        return convert_to_graphql_type(ref.field)

    @convert_to_graphql_type.register
    def _(ref: type[QueryType], **kwargs: Any) -> GraphQLType:
        return ref.__output_type__()

    @convert_to_graphql_type.register
    def _(ref: type[MutationType], **kwargs: Any) -> GraphQLType:
        if not kwargs.get("is_input", False):
            return ref.__output_type__()

        return ref.__input_type__()

    @convert_to_graphql_type.register
    def _(ref: Connection, **kwargs: Any) -> GraphQLType:
        return get_or_create_object_type(
            name=ref.query_type.__typename__ + "Connection",
            description="A connection to a list of items.",
            fields={
                "totalCount": GraphQLField(
                    GraphQLNonNull(GraphQLInt),
                    description="Total number of items in the connection.",
                ),
                "pageInfo": GraphQLField(
                    GraphQLNonNull(PageInfoType),
                    description="Information to aid in pagination.",
                ),
                "edges": GraphQLField(
                    GraphQLList(
                        GraphQLObjectType(
                            name=ref.query_type.__typename__ + "Edge",
                            description="An edge in a connection.",
                            fields=lambda: {
                                "cursor": GraphQLField(
                                    GraphQLNonNull(GraphQLString),
                                    description="A cursor for use in pagination",
                                ),
                                "node": GraphQLField(
                                    convert_to_graphql_type(ref.query_type, **kwargs),
                                    description="The item at the end of the edge",
                                ),
                            },
                        ),
                    ),
                    description="A list of edges.",
                ),
            },
            extensions={undine_settings.CONNECTION_EXTENSIONS_KEY: ref},
        )

    @convert_to_graphql_type.register
    def _(ref: Node, **kwargs: Any) -> GraphQLType:
        return ref
