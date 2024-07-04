# ruff: noqa: PLR0913
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Collection

from django.db import models
from graphql import (
    GraphQLArgument,
    GraphQLArgumentMap,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLObjectType,
    Undefined,
)

from undine.converters import convert_model_field_to_graphql_input_type
from undine.errors import MismatchingModelError, MissingModelError, TypeRegistryDuplicateError
from undine.fields import Field, Filter, Ordering
from undine.parsers import parse_model_field
from undine.settings import undine_settings
from undine.utils import TYPE_REGISTRY, get_docstring, get_members, get_schema_name

if TYPE_CHECKING:
    from undine import ModelGQLFilter, ModelGQLOrdering
    from undine.model_graphql import ModelGQLType


__all__ = [
    "ModelGQLFilterMeta",
    "ModelGQLOrderingMeta",
    "ModelGQLTypeMeta",
]


class ModelGQLTypeMeta(type):
    """A metaclass that modifies how a `ModelGQLType` is created."""

    def __new__(
        cls,
        __name: str,
        __bases: tuple[type, ...],
        __attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        filters: type[ModelGQLFilter] | None = None,
        ordering: type[ModelGQLOrdering] | None = None,
        exclude: Collection[str] = (),
        name: str | None = None,
        register: bool = True,
        auto_fields: bool = True,
        lookup_field: str | None = "pk",
        extensions: dict[str, Any] | None = None,
    ) -> ModelGQLTypeMeta:
        """See `ModelGQLType` for documentation of arguments."""
        if model is Undefined:  # Early return for the `ModelGQLType` class itself.
            return super().__new__(cls, __name, __bases, __attrs)

        if not (isinstance(model, type) and issubclass(model, models.Model)):
            raise MissingModelError(name=__name, cls="ModelGQLType")

        if auto_fields:
            cls._add_all_fields(model, __attrs, exclude)

        if filters is not None and filters.__model__ is not model:
            raise MismatchingModelError(
                cls=filters.__name__,
                bad_model=model,
                name=__name,
                expected_model=filters.__model__,
            )

        if ordering is not None and ordering.__model__ is not model:
            raise MismatchingModelError(
                cls=ordering.__name__,
                bad_model=model,
                type=__name,
                expected_model=ordering.__model__,
            )

        # Add model to attrs before class creation so that it's available during Field `__set_name__`.
        __attrs["__model__"] = model
        instance: type[ModelGQLType] = super().__new__(cls, __name, __bases, __attrs)  # type: ignore[assignment]

        if register:
            cls._register_type(model, instance)

        # Members should use '__dunder__' names to avoid name collisions with possible field names.
        instance.__model__ = model
        instance.__filters__ = filters
        instance.__ordering__ = ordering
        instance.__object_type__ = cls._create_object_type(instance, name, extensions)
        instance.__lookup_argument_map__ = cls._create_lookup_argument_map(model, lookup_field)
        return instance

    @classmethod
    def _add_all_fields(cls, model: type[models.Model], attrs: dict[str, Any], exclude: Collection[str]) -> None:
        """Add fields for all model fields, except those in exclude or already defined in the class."""
        for model_field in model._meta._get_fields():
            field_name = model_field.name
            if undine_settings.USE_PK_FIELD_NAME and getattr(model_field, "primary_key", False):
                field_name = "pk"

            if field_name in exclude or field_name in attrs:
                continue

            many = bool(model_field.many_to_many or model_field.one_to_many)
            nullable = getattr(model_field, "null", False)
            description = getattr(model_field, "help_text", None)
            attrs[field_name] = Field(model_field, description=description, many=many, nullable=nullable)

    @classmethod
    def _register_type(cls, model: type[models.Model], graphql_type: type[ModelGQLType]) -> None:
        """Registers the created ModelGQLType in the `TYPE_REGISTRY` for the given model."""
        if model in TYPE_REGISTRY:
            raise TypeRegistryDuplicateError(model=model, graphql_type=TYPE_REGISTRY[model])
        TYPE_REGISTRY[model] = graphql_type

    @classmethod
    def _create_object_type(
        cls,
        instance: type[ModelGQLType],
        name: str,
        extensions: dict[str, Any] | None,
    ) -> GraphQLObjectType:
        """
        Creates the GraphQL ObjectType for this `ModelGQLType`.

        ObjectType should be created once, since GraphQL schema cannot
        contain multiple types with the same name.
        """
        return GraphQLObjectType(
            name=name or instance.__name__,
            # Give fields as a callable to delay their creation.
            # This gives time for all ModelGQLTypes to be registered.
            fields=lambda: cls._get_fields(instance),
            description=get_docstring(instance),
            is_type_of=instance.__is_type_of__,
            extensions={
                **(extensions or {}),
                undine_settings.MODEL_TYPE_EXTENSIONS_KEY: instance,
            },
        )

    @classmethod
    def _get_fields(cls, instance: type[ModelGQLType]) -> dict[str, GraphQLField]:
        """Get the GraphQL fields for the given ModelGQLType."""
        return {get_schema_name(name): field_.get_graphql_field() for name, field_ in get_members(instance, Field)}

    @classmethod
    def _create_lookup_argument_map(cls, model: type[models.Model], lookup_field: str) -> GraphQLArgumentMap:
        """Create the lookup argument for the ModelGQLType."""
        field = model._meta.pk if lookup_field == "pk" else parse_model_field(model=model, lookup=lookup_field)
        field_name = "pk" if field.primary_key and undine_settings.USE_PK_FIELD_NAME else field.name
        return {get_schema_name(field_name): GraphQLArgument(convert_model_field_to_graphql_input_type(field))}


class ModelGQLFilterMeta(type):
    """A metaclass that modifies how a `ModelGQLFilter` is created."""

    def __new__(
        cls,
        __name: str,
        __bases: tuple[type, ...],
        __attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        auto_filters: bool = True,
        exclude: Collection[str] = (),
        name: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelGQLFilterMeta:
        """See `ModelGQLFilter` for documentation of arguments."""
        if model is Undefined:  # Early return for the `ModelGQLFilter` class itself.
            return super().__new__(cls, __name, __bases, __attrs)

        if not (isinstance(model, type) and issubclass(model, models.Model)):
            raise MissingModelError(name=__name, cls="ModelGQLFilter")

        if auto_filters:
            cls._add_all_filters(model, __attrs, exclude)

        # Add model to attrs before class creation so that it's available during Filter `__set_name__`.
        __attrs["__model__"] = model
        instance: type[ModelGQLFilter] = super().__new__(cls, __name, __bases, __attrs)  # type: ignore[assignment]

        # Members should use '__dunder__' names to avoid name collisions with possible filter names.
        instance.__model__ = model
        instance.__filter_map__ = {get_schema_name(name): ftr for name, ftr in get_members(instance, Filter)}
        instance.__input_object__ = cls._get_input_object_type(instance, name, extensions)
        return instance

    @classmethod
    def _add_all_filters(cls, model: type[models.Model], attrs: dict[str, Any], exclude: Collection[str]) -> None:
        """
        Creates filtering fields for all model non-related fields,
        except those in exclude or already defined in the class.
        """
        for model_field in model._meta._get_fields(reverse=False):
            if model_field.is_relation:
                continue

            field_name = model_field.name
            if undine_settings.USE_PK_FIELD_NAME and getattr(model_field, "primary_key", False):
                field_name = "pk"

            if field_name in exclude or field_name in attrs:
                continue

            lookup_expr: str
            for lookup_expr in model_field.get_lookups():
                filter_name = f"{field_name}_{lookup_expr}"
                description = getattr(model_field, "help_text", None)
                attrs[filter_name] = Filter(field_name, lookup_expr=lookup_expr, description=description)

    @classmethod
    def _get_input_object_type(
        cls,
        instance: type[ModelGQLFilter],
        name: str,
        extensions: dict[str, Any] | None,
    ) -> GraphQLInputObjectType:
        """
        Create the InputObjectType argument for the given `ModelGQLFilter`

        `InputObjectType` should be created once, since GraphQL schema cannot
        contain multiple types with the same name.
        """
        input_object_type = GraphQLInputObjectType(
            name=name or instance.__name__,
            description=get_docstring(instance),
            fields={},
            extensions={
                **(extensions or {}),
                undine_settings.FILTER_INPUT_EXTENSIONS_KEY: instance,
            },
        )
        input_object_type._fields = lambda: cls._get_filters(instance, input_object_type)
        return input_object_type

    @classmethod
    def _get_filters(cls, instance: type[ModelGQLFilter], iot: GraphQLInputObjectType) -> dict[str, GraphQLInputField]:
        """
        Get the filter fields for the given `ModelGQLFilter`.
        Add logical operators for combining multiple filters using the given input object type.
        """
        fields = {get_schema_name(name): filter_.as_input_field() for name, filter_ in get_members(instance, Filter)}
        fields["AND"] = fields["OR"] = fields["NOT"] = fields["XOR"] = GraphQLInputField(type_=iot)
        return fields


class ModelGQLOrderingMeta(type):
    def __new__(
        cls,
        __name: str,
        __bases: tuple[type, ...],
        __attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        auto_ordering: bool = True,
        exclude: Collection[str] = (),
        name: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelGQLOrderingMeta:
        """See `ModelGQLOrdering` for documentation of arguments."""
        if model is Undefined:  # Early return for the `ModelGQLOrdering` class itself.
            return super().__new__(cls, __name, __bases, __attrs)

        if not (isinstance(model, type) and issubclass(model, models.Model)):
            raise MissingModelError(name=__name, cls="ModelGQLOrdering")

        if auto_ordering:
            cls._add_all_orderings(model, __attrs, exclude)

        # Add model to attrs before class creation so that it's available during `ordering.__set_name__`.
        __attrs["__model__"] = model
        instance: type[ModelGQLOrdering] = super().__new__(cls, __name, __bases, __attrs)  # type: ignore[assignment]

        # Members should use '__dunder__' names to avoid name collisions with possible filter names.
        instance.__model__ = model
        instance.__ordering_map__ = {get_schema_name(n): o for n, o in get_members(instance, Ordering)}
        instance.__ordering_enum__ = cls._get_ordering_enum(instance, name, extensions)
        return instance

    @classmethod
    def _add_all_orderings(cls, model: type[models.Model], attrs: dict[str, Any], exclude: Collection[str]) -> None:
        """
        Creates ordering fields for all model non-related fields,
        except those in exclude or already defined in the class.
        """
        for model_field in model._meta._get_fields(reverse=False):
            if model_field.is_relation:
                continue

            field_name = model_field.name
            if undine_settings.USE_PK_FIELD_NAME and getattr(model_field, "primary_key", False):
                field_name = "pk"

            if field_name in exclude or field_name in attrs:
                continue

            description = getattr(model_field, "help_text", None)
            attrs[field_name] = Ordering(field_name, description=description)

    @classmethod
    def _get_ordering_enum(
        cls,
        instance: type[ModelGQLOrdering],
        name: str,
        extensions: dict[str, Any] | None,
    ) -> GraphQLEnumType:
        """
        Create the ordering `GraphQLEnum` argument for the given `ModelGQLOrdering`.

        `GraphQLEnum` should be created once, since a GraphQL schema cannot
        contain multiple types with the same name.
        """
        return GraphQLEnumType(
            name=name or instance.__name__,
            values=cls._get_enum_values(instance),
            description=get_docstring(instance),
            extensions={
                **(extensions or {}),
                undine_settings.ORDER_BY_EXTENSIONS_KEY: instance,
            },
        )

    @classmethod
    def _get_enum_values(cls, instance: type[ModelGQLOrdering]) -> dict[str, GraphQLEnumValue]:
        """
        Get all enum values for the given `ModelGQLOrdering`.
        Contains all options in both ascending and descending order.
        """
        enum_values: dict[str, GraphQLEnumValue] = {}

        for name, ordering_ in get_members(instance, Ordering):
            if not ordering_.supports_reversing:
                schema_name = get_schema_name(name)
                enum_values[schema_name] = GraphQLEnumValue(value=schema_name, description=ordering_.description)
                continue

            for direction in ("asc", "desc"):
                schema_name = get_schema_name(f"{name}_{direction}")
                enum_values[schema_name] = GraphQLEnumValue(value=schema_name, description=ordering_.description)

        return enum_values
