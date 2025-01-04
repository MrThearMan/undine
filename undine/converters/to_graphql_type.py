from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from importlib import import_module
from types import FunctionType
from typing import Any, get_args, is_typeddict

from django.db.models import (
    BinaryField,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    DurationField,
    EmailField,
    F,
    FileField,
    FloatField,
    ForeignKey,
    ImageField,
    IntegerField,
    JSONField,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    Model,
    OneToOneField,
    OneToOneRel,
    Q,
    TextChoices,
    TextField,
    TimeField,
    URLField,
    UUIDField,
)
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
    GraphQLUnionType,
)

from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion, LookupRef, TypeRef
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
from undine.typing import CombinableExpression, GQLInfo, GraphQLIOType, eval_type
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.graphql import get_or_create_graphql_enum, get_or_create_input_object_type, get_or_create_object_type
from undine.utils.model_fields import TextChoicesField
from undine.utils.model_utils import generic_relations_for_generic_foreign_key, get_model_field
from undine.utils.reflection import is_required_type
from undine.utils.text import dotpath, get_docstring, to_pascal_case

__all__ = [
    "convert_to_graphql_type",
]

convert_to_graphql_type = FunctionDispatcher[Any, GraphQLIOType]()
"""
Convert a given value to a GraphQL input type or output type.

Positional arguments:
 - ref: The reference to convert.

Keyword arguments:
 - model: The model to use for the type.
 - is_input: (Optional) Whether the type is for an input or output. Interpret as `False` if missing.
"""


# --- Python types -------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: str | type[str], **kwargs: Any) -> GraphQLIOType:
    if ref is str:
        return GraphQLString

    model_field = get_model_field(model=kwargs["model"], lookup=ref)
    return convert_to_graphql_type(model_field, **kwargs)


@convert_to_graphql_type.register
def _(_: type[bool], **kwargs: Any) -> GraphQLIOType:
    return GraphQLBoolean


@convert_to_graphql_type.register
def _(_: type[int], **kwargs: Any) -> GraphQLIOType:
    return GraphQLInt


@convert_to_graphql_type.register
def _(_: type[float], **kwargs: Any) -> GraphQLIOType:
    return GraphQLFloat


@convert_to_graphql_type.register
def _(_: type[Decimal], **kwargs: Any) -> GraphQLIOType:
    return GraphQLDecimal


@convert_to_graphql_type.register
def _(_: type[datetime.datetime], **kwargs: Any) -> GraphQLIOType:
    return GraphQLDateTime


@convert_to_graphql_type.register
def _(_: type[datetime.date], **kwargs: Any) -> GraphQLIOType:
    return GraphQLDate


@convert_to_graphql_type.register
def _(_: type[datetime.time], **kwargs: Any) -> GraphQLIOType:
    return GraphQLTime


@convert_to_graphql_type.register
def _(_: type[datetime.timedelta], **kwargs: Any) -> GraphQLIOType:
    return GraphQLDuration


@convert_to_graphql_type.register
def _(_: type[uuid.UUID], **kwargs: Any) -> GraphQLIOType:
    return GraphQLUUID


@convert_to_graphql_type.register
def _(ref: type[Enum], **kwargs: Any) -> GraphQLIOType:
    return get_or_create_graphql_enum(
        name=ref.__name__,
        values={name: value.value for name, value in ref.__members__.items()},
        description=get_docstring(ref),
    )


@convert_to_graphql_type.register
def _(ref: type[TextChoices], **kwargs: Any) -> GraphQLIOType:
    return get_or_create_graphql_enum(
        name=ref.__name__,
        values=dict(ref.choices),
        description=get_docstring(ref),
    )


@convert_to_graphql_type.register
def _(_: type, **kwargs: Any) -> GraphQLIOType:
    return GraphQLAny


@convert_to_graphql_type.register
def _(ref: type[list], **kwargs: Any) -> GraphQLIOType:
    args = get_args(ref)
    # For lists without type, or with a union type, default to any.
    if len(args) != 1:
        return GraphQLList(GraphQLAny)

    graphql_type, nullable = convert_to_graphql_type(args[0], return_nullable=True, **kwargs)
    if not nullable:
        graphql_type = GraphQLNonNull(graphql_type)
    return GraphQLList(graphql_type)


@convert_to_graphql_type.register
def _(ref: type[dict], **kwargs: Any) -> GraphQLIOType:
    if not is_typeddict(ref):
        return GraphQLJSON

    module_globals = vars(import_module(ref.__module__))
    is_input = kwargs.get("is_input", False)
    total: bool = getattr(ref, "__total__", True)

    fields: dict[str, GraphQLField | GraphQLInputField] = {}
    for key, value in ref.__annotations__.items():
        evaluated_type = eval_type(value, globals_=module_globals)
        graphql_type, nullable = convert_to_graphql_type(evaluated_type, return_nullable=True, **kwargs)

        if not total and not is_required_type(evaluated_type):
            nullable = True

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
def _(ref: CharField, **kwargs: Any) -> GraphQLIOType:
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
def _(_: TextField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLString


@convert_to_graphql_type.register
def _(ref: TextChoicesField, **kwargs: Any) -> GraphQLIOType:
    return get_or_create_graphql_enum(
        name=ref.choices_enum.__name__,
        values=dict(ref.choices),
        description=getattr(ref, "help_text", None) or get_docstring(ref.choices_enum),
    )


@convert_to_graphql_type.register
def _(_: BooleanField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLBoolean


@convert_to_graphql_type.register
def _(_: IntegerField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLInt


@convert_to_graphql_type.register
def _(_: FloatField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLFloat


@convert_to_graphql_type.register
def _(_: DecimalField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLDecimal


@convert_to_graphql_type.register
def _(_: DateField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLDate


@convert_to_graphql_type.register
def _(_: DateTimeField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLDateTime


@convert_to_graphql_type.register
def _(_: TimeField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLTime


@convert_to_graphql_type.register
def _(_: DurationField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLDuration


@convert_to_graphql_type.register
def _(_: UUIDField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLUUID


@convert_to_graphql_type.register
def _(_: EmailField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLEmail


@convert_to_graphql_type.register
def _(_: URLField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLURL


@convert_to_graphql_type.register
def _(_: BinaryField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLBase64


@convert_to_graphql_type.register
def _(_: JSONField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLJSON


@convert_to_graphql_type.register
def _(_: FileField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLFile


@convert_to_graphql_type.register
def _(_: ImageField, **kwargs: Any) -> GraphQLIOType:
    return GraphQLImage


@convert_to_graphql_type.register
def _(ref: OneToOneField, **kwargs: Any) -> GraphQLIOType:
    return convert_to_graphql_type(ref.target_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: ForeignKey, **kwargs: Any) -> GraphQLIOType:
    return convert_to_graphql_type(ref.target_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: ManyToManyField, **kwargs: Any) -> GraphQLIOType:
    type_ = convert_to_graphql_type(ref.target_field, **kwargs)
    return GraphQLList(GraphQLNonNull(type_))


@convert_to_graphql_type.register
def _(ref: OneToOneRel, **kwargs: Any) -> GraphQLIOType:
    return convert_to_graphql_type(ref.target_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: ManyToOneRel, **kwargs: Any) -> GraphQLIOType:
    type_ = convert_to_graphql_type(ref.target_field, **kwargs)
    return GraphQLList(GraphQLNonNull(type_))


@convert_to_graphql_type.register
def _(ref: ManyToManyRel, **kwargs: Any) -> GraphQLIOType:
    type_ = convert_to_graphql_type(ref.target_field, **kwargs)
    return GraphQLList(GraphQLNonNull(type_))


# --- Django ORM ---------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: F, **kwargs: Any) -> GraphQLIOType:
    model: type[Model] = kwargs["model"]
    model_field = get_model_field(model=model, lookup=ref.name)
    return convert_to_graphql_type(model_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: CombinableExpression, **kwargs: Any) -> GraphQLIOType:
    return convert_to_graphql_type(ref.output_field, **kwargs)


@convert_to_graphql_type.register
def _(_: Q, **kwargs: Any) -> GraphQLIOType:
    return GraphQLBoolean


@convert_to_graphql_type.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> GraphQLIOType:
    return convert_to_graphql_type(ref.field, **kwargs)


@convert_to_graphql_type.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> GraphQLIOType:
    return convert_to_graphql_type(ref.rel, **kwargs)


@convert_to_graphql_type.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> GraphQLIOType:
    return convert_to_graphql_type(ref.related, **kwargs)


@convert_to_graphql_type.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> GraphQLIOType:
    return convert_to_graphql_type(ref.rel if ref.reverse else ref.field, **kwargs)


# --- GraphQL types ------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: GraphQLIOType, **kwargs: Any) -> GraphQLIOType:
    return ref


# --- Custom types -------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: LazyQueryType, **kwargs: Any) -> GraphQLIOType:
    return convert_to_graphql_type(ref.get_type(), **kwargs)


@convert_to_graphql_type.register
def _(ref: LazyQueryTypeUnion, **kwargs: Any) -> GraphQLUnionType:
    def resolve_type(obj: type[Model], info: GQLInfo, union_type: GraphQLUnionType) -> Any:
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
def _(ref: LazyLambdaQueryType, **kwargs: Any) -> GraphQLIOType:
    return convert_to_graphql_type(ref.callback(), **kwargs)


@convert_to_graphql_type.register
def _(ref: TypeRef, **kwargs: Any) -> GraphQLIOType:
    kwargs["return_nullable"] = True
    value, nullable = convert_to_graphql_type(ref.value, **kwargs)
    if not nullable:
        value = GraphQLNonNull(value)
    return value


@convert_to_graphql_type.register
def _(ref: Calculated, **kwargs: Any) -> GraphQLIOType:
    kwargs["return_nullable"] = True
    value, nullable = convert_to_graphql_type(ref.returns, **kwargs)
    if not nullable:
        value = GraphQLNonNull(value)
    return value


# --- Deferred -----------------------------------------------------------------------------------------------------


def load_deferred() -> None:  # noqa: C901
    # See. `undine.apps.UndineConfig.load_deferred()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation

    from undine import MutationType, QueryType
    from undine.converters import convert_lookup_to_graphql_type, convert_to_python_type
    from undine.parsers import parse_first_param_type, parse_return_annotation
    from undine.relay import Connection, Node, PageInfoType

    @convert_to_graphql_type.register
    def _(ref: FunctionType, **kwargs: Any) -> GraphQLIOType:
        is_input = kwargs.get("is_input", False)
        annotation = parse_first_param_type(ref) if is_input else parse_return_annotation(ref)
        return convert_to_graphql_type(annotation, **kwargs)

    @convert_to_graphql_type.register
    def _(ref: LookupRef, **kwargs: Any) -> GraphQLIOType:
        kwargs["default_type"] = convert_to_python_type(ref.ref, **kwargs)
        return convert_lookup_to_graphql_type(ref.lookup, **kwargs)

    @convert_to_graphql_type.register
    def _(ref: GenericForeignKey, **kwargs: Any) -> GraphQLIOType:
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
    def _(ref: GenericRelation, **kwargs: Any) -> GraphQLIOType:
        object_id_field = ref.related_model._meta.get_field(ref.object_id_field_name)
        type_ = convert_to_graphql_type(object_id_field, **kwargs)
        return GraphQLList(type_)

    @convert_to_graphql_type.register
    def _(ref: GenericRel, **kwargs: Any) -> GraphQLIOType:
        return convert_to_graphql_type(ref.field)

    @convert_to_graphql_type.register
    def _(ref: type[QueryType], **kwargs: Any) -> GraphQLIOType:
        return ref.__output_type__()

    @convert_to_graphql_type.register
    def _(ref: type[MutationType], **kwargs: Any) -> GraphQLIOType:
        if not kwargs.get("is_input", False):
            return ref.__output_type__()

        return ref.__input_type__()

    @convert_to_graphql_type.register
    def _(ref: Connection, **kwargs: Any) -> GraphQLIOType:
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
                    description="Information about the current state of the pagination.",
                ),
                "edges": GraphQLField(
                    GraphQLList(
                        GraphQLObjectType(
                            name=ref.query_type.__typename__ + "Edge",
                            description="An object describing an item in the connection.",
                            fields=lambda: {
                                "cursor": GraphQLField(
                                    GraphQLNonNull(GraphQLString),
                                    description="A value identifying this edge for pagination purposes.",
                                ),
                                "node": GraphQLField(
                                    convert_to_graphql_type(ref.query_type, **kwargs),
                                    description="An item in the connection.",
                                ),
                            },
                        ),
                    ),
                    description="The items in the connection.",
                ),
            },
            extensions={undine_settings.CONNECTION_EXTENSIONS_KEY: ref},
        )

    @convert_to_graphql_type.register
    def _(ref: Node, **kwargs: Any) -> GraphQLIOType:
        return ref

    # Postgres fields
    try:
        from django.contrib.postgres.fields import ArrayField, HStoreField

        @convert_to_graphql_type.register
        def _(_: HStoreField, **kwargs: Any) -> GraphQLIOType:
            return GraphQLJSON

        @convert_to_graphql_type.register
        def _(ref: ArrayField, **kwargs: Any) -> GraphQLIOType:
            inner_type = convert_to_graphql_type(ref.base_field, **kwargs)
            if not ref.base_field.null:
                inner_type = GraphQLNonNull(inner_type)
            return GraphQLList(inner_type)

    except ImportError:  # pragma: no cover
        pass

    # Generated field
    try:
        from django.db.models import GeneratedField

        @convert_to_graphql_type.register
        def _(ref: GeneratedField, **kwargs: Any) -> GraphQLIOType:
            return convert_to_graphql_type(ref.output_field, **kwargs)

    except ImportError:  # pragma: no cover
        pass
