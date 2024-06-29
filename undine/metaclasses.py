from __future__ import annotations

from typing import TYPE_CHECKING, Any, Collection

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from graphql import GraphQLArgument, GraphQLArgumentMap, Undefined

from undine.converters import convert_model_field_to_type, convert_type_to_graphql_input_type
from undine.fields import Field
from undine.settings import undine_settings
from undine.utils import dotpath, get_members, get_schema_name

if TYPE_CHECKING:
    from undine import ModelGQLFilters
    from undine.types import ModelGQLType


__all__ = [
    "ModelGQLFiltersMeta",
    "ModelGQLTypeMeta",
]


class ModelGQLTypeMeta(type):
    """
    A metaclass that modifies how ModelGQLTypes are created:

    1) Automatically creates graphql fields for all model fields, except those in give `exclude` list.
    2) Registers the created type in the `ModelGQLTypeMeta.type_registry` so that
       related fields can access them when they are created.
    3) Add the given model class to the created ModelGQLType as an attribute.
    """

    type_registry: dict[type[models.Model], type[ModelGQLType]] = {}
    """Maps Django model classes to their corresponding ModelGQLTypes."""

    def __new__(  # noqa: PLR0913
        cls,
        __name: str,
        __bases: tuple[type, ...],
        __attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        filters: type[ModelGQLFilters] | None = None,
        exclude: Collection[str] = (),
        name: str | None = None,
        register: bool = True,
        create_fields: bool = True,
        lookup_field: str | None = "pk",
    ) -> ModelGQLTypeMeta:
        """
        Args after '*' can be passed in the class definition

        >>> class MyType(ModelGQLType, model=MyModel): ...

        :param model: Set the Django model this ModelGQLType represents.
        :param exclude: List of fields to exclude from the GraphQL schema.
        :param name: Override name for the ModelGQLType in the GraphQL schema. Use class name by default.
        :param register: Whether to register the ModelGQLType in `type_registry`.
        :param create_fields: Whether to create fields for all model fields automatically.
        :param lookup_field: Name of the field to use for looking up single objects.
        """
        if model is Undefined:  # Early return for the ModelGQLType class itself.
            return super().__new__(cls, __name, __bases, __attrs)

        if isinstance(model, type) and not issubclass(model, models.Model):
            msg = (
                "When subclassing `ModelGQLType`, you need to provide the model class as a keyword argument "
                "to the class definition, e.g. `class MyType(ModelGQLType, model=MyModel)`."
            )
            raise TypeError(msg)

        if create_fields:
            cls._create_fields(model, __attrs, exclude)

        if filters is not None and filters.__model__ is not model:
            msg = (
                f"'{__name}' model '{dotpath(model)}' does not match "
                f"the model of the given `ModelGQLFilters`: '{dotpath(filters.__model__)}'."
            )
            raise ValueError(msg)

        graphql_type = super().__new__(cls, __name, __bases, __attrs)

        if register:
            cls._register_type(model, graphql_type)  # type: ignore[arg-type]

        # Members should use '__dunder__' names to avoid name collisions with possible field names.
        graphql_type.__model__ = model
        graphql_type.__filters__ = filters.__filters__ if filters is not None else {}
        graphql_type.__graphql_name__ = name or graphql_type.__name__
        graphql_type.__lookup_argument__ = cls._create_lookup_argument(model, lookup_field)
        return graphql_type

    @classmethod
    def _create_fields(cls, model: type[models.Model], attrs: dict[str, Any], exclude: Collection[str]) -> None:
        """Creates fields for all model fields, except those in exclude or already defined in the class."""
        for field in model._meta._get_fields():  # noqa: SLF001
            field_name = field.name

            if undine_settings.USE_PK_FIELD_NAME and getattr(field, "primary_key", False):
                field_name = "pk"

            if field_name in exclude or field_name in attrs:
                continue

            many = bool(field.many_to_many or field.one_to_many)
            nullable = getattr(field, "null", False)
            description = getattr(field, "help_text", None)
            attrs[field_name] = Field(field, description=description, many=many, nullable=nullable)

    @classmethod
    def _register_type(cls, model: type[models.Model], graphql_type: type[ModelGQLType]) -> None:
        """Registers the created ModelGQLType in `type_registry` for the given model."""
        if model in cls.type_registry:
            graphql_type = cls.type_registry[model]
            msg = (
                f"A ModelGQLType for model '{dotpath(model)}' "
                f"has already been registered: '{dotpath(graphql_type)}'. "
                f"Use a proxy model or disable registration with "
                f"`class MyType(ModelGQLType, model=MyModel, register=False)`."
            )
            raise ValueError(msg)

        cls.type_registry[model] = graphql_type  # type: ignore[assignment]

    @classmethod
    def _create_lookup_argument(cls, model: type[models.Model], lookup_field: str) -> GraphQLArgumentMap:
        """Create the lookup argument for the ModelGQLType."""
        try:
            field: models.Field = model._meta.pk if lookup_field == "pk" else model._meta.get_field(lookup_field)
        except FieldDoesNotExist as error:
            msg = f"Field '{lookup_field}' does not exist in model '{dotpath(model)}'."
            raise ValueError(msg) from error

        field_name = "pk" if field.primary_key and undine_settings.USE_PK_FIELD_NAME else field.name
        field_type = convert_model_field_to_type(field)
        return {
            get_schema_name(field_name): GraphQLArgument(
                type_=convert_type_to_graphql_input_type(field_type),
                description=getattr(field, "help_text", None),
            )
        }


class ModelGQLFiltersMeta(type):
    """A metaclass that modifies how ModelGQLFilters are created:"""

    def __new__(
        cls,
        __name: str,
        __bases: tuple[type, ...],
        __attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
    ) -> ModelGQLFiltersMeta:
        """
        Args after '*' can be passed in the class definition,

        >>> class MyFilters(ModelGQLFilters, model=MyModel): ...

        :param model: Set the Django model this ModelGQLFilters is for.
        """
        if model is Undefined:  # Early return for the ModelGQLType class itself.
            return super().__new__(cls, __name, __bases, __attrs)

        if isinstance(model, type) and not issubclass(model, models.Model):
            msg = (
                "When subclassing `ModelGQLFilters`, you need to provide the model class as a keyword argument "
                "to the class definition, e.g. `class MyFilters(ModelGQLFilters, model=MyModel)`."
            )
            raise TypeError(msg)

        # TODO: Add all possible filters?

        filters = super().__new__(cls, __name, __bases, __attrs)

        from undine import Filter

        # Members should use '__dunder__' names to avoid name collisions with possible filter names.
        filters.__model__ = model
        filters.__filters__ = {get_schema_name(name): ftr for name, ftr in get_members(filters, Filter)}
        return filters
