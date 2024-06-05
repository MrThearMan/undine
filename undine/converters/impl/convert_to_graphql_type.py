from __future__ import annotations

import datetime
import uuid
from contextlib import suppress
from decimal import Decimal
from enum import Enum
from functools import partial
from importlib import import_module
from types import FunctionType
from typing import Any, get_args, is_typeddict

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation
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
    GenericIPAddressField,
    ImageField,
    IntegerField,
    IPAddressField,
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
    GraphQLField,
    GraphQLFloat,
    GraphQLInputField,
    GraphQLInputType,
    GraphQLInt,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLOutputType,
    GraphQLString,
)

from undine import Calculation, InterfaceType, MutationType, QueryType, UnionType
from undine.converters import convert_lookup_to_graphql_type, convert_to_graphql_type, convert_to_python_type
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, LookupRef, MaybeManyOrNonNull, TypeRef
from undine.exceptions import RegistryMissingTypeError
from undine.mutation import MutationTypeMeta
from undine.parsers import parse_first_param_type, parse_is_nullable, parse_return_annotation
from undine.relay import Connection, PageInfoType
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
    GraphQLIP,
    GraphQLIPv4,
    GraphQLIPv6,
    GraphQLJSON,
    GraphQLTime,
    GraphQLURL,
    GraphQLUUID,
)
from undine.settings import undine_settings
from undine.typing import CombinableExpression, ModelField, eval_type
from undine.utils.graphql.type_registry import (
    get_or_create_graphql_enum,
    get_or_create_graphql_input_object_type,
    get_or_create_graphql_object_type,
)
from undine.utils.graphql.validation_rules.one_of_input_object import (
    get_one_of_input_object_type_extension,
    validate_one_of_input_object_variable_value,
)
from undine.utils.model_fields import TextChoicesField
from undine.utils.model_utils import generic_relations_for_generic_foreign_key, get_model_field
from undine.utils.reflection import FunctionEqualityWrapper, is_generic_list, is_required_type
from undine.utils.text import get_docstring, to_camel_case, to_pascal_case

# --- Python types -------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: str, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    model_field = get_model_field(model=kwargs["model"], lookup=ref)
    return convert_to_graphql_type(model_field, **kwargs)


@convert_to_graphql_type.register
def _(_: type[str], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLString


@convert_to_graphql_type.register
def _(_: type[bool], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLBoolean


@convert_to_graphql_type.register
def _(_: type[int], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLInt


@convert_to_graphql_type.register
def _(_: type[float], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLFloat


@convert_to_graphql_type.register
def _(_: type[Decimal], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLDecimal


@convert_to_graphql_type.register
def _(_: type[datetime.datetime], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLDateTime


@convert_to_graphql_type.register
def _(_: type[datetime.date], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLDate


@convert_to_graphql_type.register
def _(_: type[datetime.time], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLTime


@convert_to_graphql_type.register
def _(_: type[datetime.timedelta], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLDuration


@convert_to_graphql_type.register
def _(_: type[uuid.UUID], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLUUID


@convert_to_graphql_type.register
def _(ref: type[Enum], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return get_or_create_graphql_enum(
        name=ref.__name__,
        values={name: value.value for name, value in ref.__members__.items()},
        description=get_docstring(ref),
    )


@convert_to_graphql_type.register
def _(ref: type[TextChoices], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return get_or_create_graphql_enum(
        name=ref.__name__,
        values={key: str(value) for key, value in ref.choices},
        description=get_docstring(ref),
    )


@convert_to_graphql_type.register
def _(_: type, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLAny


@convert_to_graphql_type.register
def _(ref: type[list], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    args = get_args(ref)
    # For lists without type, or with a union type, default to any.
    if len(args) != 1:
        return GraphQLList(GraphQLAny)

    graphql_type = convert_to_graphql_type(args[0], **kwargs)
    nullable = parse_is_nullable(args[0], is_input=kwargs.get("is_input", False))

    if not nullable:
        graphql_type = GraphQLNonNull(graphql_type)
    return GraphQLList(graphql_type)


@convert_to_graphql_type.register
def _(ref: type[dict], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    if not is_typeddict(ref):
        return GraphQLJSON

    module_globals = vars(import_module(ref.__module__))
    is_input = kwargs.get("is_input", False)
    total: bool = getattr(ref, "__total__", True)

    fields: dict[str, GraphQLField | GraphQLInputField] = {}
    for key, value in ref.__annotations__.items():
        evaluated_type = eval_type(value, globals_=module_globals)
        graphql_type = convert_to_graphql_type(evaluated_type, **kwargs)
        nullable = parse_is_nullable(evaluated_type, is_input=kwargs.get("is_input", False))

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
        return get_or_create_graphql_input_object_type(
            name=ref.__name__,
            fields=fields,
            description=description,
        )

    return get_or_create_graphql_object_type(
        name=ref.__name__,
        fields=fields,
        description=description,
    )


@convert_to_graphql_type.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    is_input = kwargs.get("is_input", False)
    annotation = parse_first_param_type(ref) if is_input else parse_return_annotation(ref)
    return convert_to_graphql_type(annotation, **kwargs)


# --- Model fields -------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: CharField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    if ref.choices is None:
        return GraphQLString

    # Generate a name for an enum based on the field it is used in.
    # This is required, since CharField doesn't know the name of the enum it is used in.
    # Use `TextChoicesField` instead to not get multiple enums in the GraphQL schema for different fields.
    name = ref.model.__name__ + to_pascal_case(ref.name) + "Choices"

    return get_or_create_graphql_enum(
        name=name,
        values={key: str(value) for key, value in ref.choices},
        description=getattr(ref, "help_text", None) or None,
    )


@convert_to_graphql_type.register
def _(_: TextField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLString


@convert_to_graphql_type.register
def _(ref: TextChoicesField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return get_or_create_graphql_enum(
        name=ref.choices_enum.__name__,
        values={key: str(value) for key, value in ref.choices_enum.choices},
        description=getattr(ref, "help_text", None) or get_docstring(ref.choices_enum),
    )


@convert_to_graphql_type.register
def _(_: BooleanField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLBoolean


@convert_to_graphql_type.register
def _(_: IntegerField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLInt


@convert_to_graphql_type.register
def _(_: FloatField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLFloat


@convert_to_graphql_type.register
def _(_: DecimalField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLDecimal


@convert_to_graphql_type.register
def _(_: DateField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLDate


@convert_to_graphql_type.register
def _(_: DateTimeField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLDateTime


@convert_to_graphql_type.register
def _(_: TimeField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLTime


@convert_to_graphql_type.register
def _(_: DurationField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLDuration


@convert_to_graphql_type.register
def _(_: UUIDField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLUUID


@convert_to_graphql_type.register
def _(_: EmailField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLEmail


@convert_to_graphql_type.register
def _(_: IPAddressField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLIPv4


@convert_to_graphql_type.register
def _(ref: GenericIPAddressField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    if ref.protocol.lower() == "ipv4":
        return GraphQLIPv4
    if ref.protocol.lower() == "ipv6":
        return GraphQLIPv6
    return GraphQLIP


@convert_to_graphql_type.register
def _(_: URLField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLURL


@convert_to_graphql_type.register
def _(_: BinaryField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLBase64


@convert_to_graphql_type.register
def _(_: JSONField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLJSON


@convert_to_graphql_type.register
def _(_: FileField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLFile


@convert_to_graphql_type.register
def _(_: ImageField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLImage


@convert_to_graphql_type.register
def _(ref: OneToOneField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return convert_to_graphql_type(ref.target_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: ForeignKey, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return convert_to_graphql_type(ref.target_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: ManyToManyField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    type_ = convert_to_graphql_type(ref.target_field, **kwargs)
    return GraphQLList(GraphQLNonNull(type_))


@convert_to_graphql_type.register
def _(ref: OneToOneRel, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return convert_to_graphql_type(ref.target_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: ManyToOneRel, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    type_ = convert_to_graphql_type(ref.target_field, **kwargs)
    return GraphQLList(GraphQLNonNull(type_))


@convert_to_graphql_type.register
def _(ref: ManyToManyRel, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    type_ = convert_to_graphql_type(ref.target_field, **kwargs)
    return GraphQLList(GraphQLNonNull(type_))


@convert_to_graphql_type.register
def _(ref: GenericForeignKey, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    if not kwargs.get("is_input"):
        field: ModelField = ref.model._meta.get_field(ref.fk_field)
        return convert_to_graphql_type(field, **kwargs)

    fk_field_name = to_pascal_case(ref.name)
    input_object_name = f"{ref.model.__name__}{fk_field_name}Input"

    related_models = [field.model for field in generic_relations_for_generic_foreign_key(ref)]

    def fields() -> dict[str, GraphQLInputField]:
        field_map: dict[str, GraphQLInputField] = {}

        for model in related_models:
            schema_name = f"{ref.model.__name__}{fk_field_name}{model.__name__}Input"

            MutationTypeMeta.__model__ = model

            class RelatedMutation(MutationType, kind="related", schema_name=schema_name): ...

            field_name = to_camel_case(model.__name__)
            input_type = RelatedMutation.__input_type__()

            field_map[field_name] = GraphQLInputField(input_type)

        return field_map

    return get_or_create_graphql_input_object_type(
        name=input_object_name,
        fields=FunctionEqualityWrapper(fields, context=ref),
        extensions=get_one_of_input_object_type_extension(),
        out_type=partial(validate_one_of_input_object_variable_value, typename=input_object_name),
    )


@convert_to_graphql_type.register
def _(ref: GenericRelation, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    object_id_field = ref.related_model._meta.get_field(ref.object_id_field_name)
    type_ = convert_to_graphql_type(object_id_field, **kwargs)
    return GraphQLList(type_)


@convert_to_graphql_type.register
def _(ref: GenericRel, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return convert_to_graphql_type(ref.field)


# Postgres fields
with suppress(ImportError):
    from django.contrib.postgres.fields import ArrayField, HStoreField

    @convert_to_graphql_type.register
    def _(_: HStoreField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
        return GraphQLJSON

    @convert_to_graphql_type.register
    def _(ref: ArrayField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
        inner_type = convert_to_graphql_type(ref.base_field, **kwargs)
        if not ref.base_field.null:
            inner_type = GraphQLNonNull(inner_type)
        return GraphQLList(inner_type)


# Generated field
with suppress(ImportError):
    from django.db.models import GeneratedField

    @convert_to_graphql_type.register
    def _(ref: GeneratedField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
        return convert_to_graphql_type(ref.output_field, **kwargs)


# --- Django ORM ---------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: F, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    model: type[Model] = kwargs["model"]
    model_field = get_model_field(model=model, lookup=ref.name)
    return convert_to_graphql_type(model_field, **kwargs)


@convert_to_graphql_type.register
def _(_: Q, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLBoolean


@convert_to_graphql_type.register
def _(ref: CombinableExpression, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return convert_to_graphql_type(ref.output_field, **kwargs)


@convert_to_graphql_type.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return convert_to_graphql_type(ref.field, **kwargs)


@convert_to_graphql_type.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return convert_to_graphql_type(ref.rel, **kwargs)


@convert_to_graphql_type.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return convert_to_graphql_type(ref.related, **kwargs)


@convert_to_graphql_type.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return convert_to_graphql_type(ref.rel if ref.reverse else ref.field, **kwargs)


# --- GraphQL types ------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: GraphQLInputType | GraphQLOutputType, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return ref


@convert_to_graphql_type.register
def _(ref: GraphQLInterfaceType, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return ref


# --- Custom types -------------------------------------------------------------------------------------------------


@convert_to_graphql_type.register
def _(ref: type[QueryType], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return ref.__output_type__()


@convert_to_graphql_type.register
def _(ref: type[MutationType], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    if not kwargs.get("is_input"):
        return ref.__output_type__()

    return ref.__input_type__()


@convert_to_graphql_type.register
def _(ref: type[UnionType], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return ref.__union_type__()


@convert_to_graphql_type.register
def _(ref: LazyRelation, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    try:
        value = ref.get_type()
    except RegistryMissingTypeError:
        value = ref.field

    return convert_to_graphql_type(value, **kwargs)


@convert_to_graphql_type.register
def _(ref: LazyGenericForeignKey, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    name = ref.field.model.__name__ + to_pascal_case(ref.field.name)

    type(UnionType).__query_types__ = ref.get_types()

    class GenericUnion(UnionType, schema_name=name): ...

    return convert_to_graphql_type(GenericUnion)


@convert_to_graphql_type.register
def _(ref: LazyLambda, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return convert_to_graphql_type(ref.callback(), **kwargs)


@convert_to_graphql_type.register
def _(ref: TypeRef, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    value = convert_to_graphql_type(ref.value, **kwargs)
    nullable = parse_is_nullable(ref.value, is_input=kwargs.get("is_input", False))
    if not nullable:
        value = GraphQLNonNull(value)
    return value


@convert_to_graphql_type.register
def _(ref: MaybeManyOrNonNull, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    value = convert_to_graphql_type(ref.value, **kwargs)

    # Note that order matters here!
    if ref.many is True and not isinstance(value, GraphQLList):
        if not isinstance(value, GraphQLNonNull):
            value = GraphQLNonNull(value)
        value = GraphQLList(value)

    if ref.nullable is False and not isinstance(value, GraphQLNonNull):
        value = GraphQLNonNull(value)

    return value


@convert_to_graphql_type.register
def _(ref: type[Calculation], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    value = convert_to_graphql_type(ref.__returns__, **kwargs)
    nullable = parse_is_nullable(ref.__returns__, is_input=kwargs.get("is_input", False))
    if not nullable:
        value = GraphQLNonNull(value)
    return value


@convert_to_graphql_type.register
def _(ref: LookupRef, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    default_type = convert_to_python_type(ref.ref, **kwargs)

    many = is_generic_list(default_type)
    if many:
        default_type = default_type.__args__[0]

    kwargs["default_type"] = default_type
    kwargs["many"] = many
    return convert_lookup_to_graphql_type(ref.lookup, **kwargs)


@convert_to_graphql_type.register
def _(ref: Connection, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return get_or_create_graphql_object_type(
        name=f"{ref.query_type.__schema_name__}Connection",
        description="A connection to a list of items.",
        fields={
            undine_settings.TOTAL_COUNT_PARAM_NAME: GraphQLField(
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
                        name=f"{ref.query_type.__schema_name__}Edge",
                        description="An object describing an item in the connection.",
                        fields=lambda: {
                            "cursor": GraphQLField(
                                GraphQLNonNull(GraphQLString),
                                description="A value identifying this edge for pagination purposes.",
                            ),
                            "node": GraphQLField(
                                convert_to_graphql_type(ref.query_type, **kwargs),  # type: ignore[arg-type]
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
def _(ref: type[InterfaceType], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return ref.__interface__()
