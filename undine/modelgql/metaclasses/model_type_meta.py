from __future__ import annotations

from typing import TYPE_CHECKING, Any, Collection, Literal

from graphql import GraphQLArgument, GraphQLArgumentMap, GraphQLField, GraphQLObjectType, Undefined

from undine.converters import convert_model_field_to_graphql_input_type
from undine.errors import MismatchingModelError, MissingModelError, TypeRegistryDuplicateError
from undine.fields import Field
from undine.parsers import parse_model_field
from undine.settings import undine_settings
from undine.utils.reflection import get_members
from undine.utils.registry import TYPE_REGISTRY
from undine.utils.text import get_docstring, get_schema_name

if TYPE_CHECKING:
    from django.db import models

    from undine.modelgql.model_filter import ModelGQLFilter
    from undine.modelgql.model_ordering import ModelGQLOrdering
    from undine.modelgql.model_type import ModelGQLType


__all__ = [
    "ModelGQLTypeMeta",
]


class ModelGQLTypeMeta(type):
    """A metaclass that modifies how a `ModelGQLType` is created."""

    def __new__(  # noqa: PLR0913
        cls,
        __name: str,
        __bases: tuple[type, ...],
        __attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        filters: type[ModelGQLFilter] | Literal[True] | None = None,
        ordering: type[ModelGQLOrdering] | Literal[True] | None = None,
        auto_fields: bool = True,
        exclude: Collection[str] = (),
        lookup_field: str | None = "pk",
        name: str | None = None,
        register: bool = True,
        extensions: dict[str, Any] | None = None,
    ) -> ModelGQLTypeMeta:
        """See `ModelGQLType` for documentation of arguments."""
        if model is Undefined:  # Early return for the `ModelGQLType` class itself.
            return super().__new__(cls, __name, __bases, __attrs)

        if model is None:
            raise MissingModelError(name=__name, cls="ModelGQLType")

        if auto_fields:
            cls._add_all_fields(model, __attrs, exclude)

        filters = cls._validate_filters(filters, model, __name)
        ordering = cls._validate_ordering(ordering, model, __name)

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

    @staticmethod
    def _validate_filters(
        filters: type[ModelGQLFilter] | Literal[True] | None,
        model: type[models.Model],
        name: str,
    ) -> type[ModelGQLFilter] | None:
        """Validate the given filters class."""
        if filters is True:
            from undine import ModelGQLFilter

            filters = type(f"{model.__name__}Filter", (ModelGQLFilter,), {}, model=model)

        if filters is not None and filters.__model__ is not model:
            raise MismatchingModelError(
                cls=filters.__name__,
                bad_model=model,
                name=name,
                expected_model=filters.__model__,
            )

        return filters

    @staticmethod
    def _validate_ordering(
        ordering: type[ModelGQLOrdering] | Literal[True] | None,
        model: type[models.Model],
        name: str,
    ) -> type[ModelGQLOrdering] | None:
        """Validate the given ordering class."""
        if ordering is True:
            from undine import ModelGQLOrdering

            ordering = type(f"{model.__name__}Ordering", (ModelGQLOrdering,), {}, model=model)

        if ordering is not None and ordering.__model__ is not model:
            raise MismatchingModelError(
                cls=ordering.__name__,
                bad_model=model,
                type=name,
                expected_model=ordering.__model__,
            )

        return ordering

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
