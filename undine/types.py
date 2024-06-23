from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Collection

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from graphql import GraphQLField, GraphQLObjectType, GraphQLResolveInfo, Undefined

from undine.errors import handle_get_errors
from undine.field import Field, get_fields_from_class
from undine.settings import undine_settings
from undine.utils import dotpath

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation

    from undine.typing import ToManyField, ToOneField

__all__ = [
    "ModelGQLType",
]


class ModelGQLTypeMeta(type):
    """
    A metaclass that modifies how ModelGQLTypes are created:

    1) Automatically creates Fields for all model fields, except those in give `exclude` list.
    2) Registers the created node in the `ModelGQLTypeMeta.node_registry` so that
       related fields can access them when they are created.
    """

    node_registry: dict[type[models.Model], type[ModelGQLType]] = {}
    """Maps Django model classes to their corresponding ModelGQLTypes."""

    def __new__(  # noqa: PLR0913
        cls,
        __name: str,
        __bases: tuple[type, ...],
        __attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        exclude: Collection[str] = (),
        name: str | None = None,
        register: bool = True,
        create_fields: bool = True,
        lookup_field: str | None = "pk",
    ) -> ModelGQLTypeMeta:
        """
        Args after '*' can be passed in the class definition, e.g. `class MyNode(ModelGQLType, model=MyModel)`.

        :param model: Set the Django model this node represents.
        :param exclude: List of fields to exclude from the GraphQL schema.
        :param name: Override name for the node in the GraphQL schema. Use class name by default.
        :param register: Whether to register the node in the node registry.
        :param create_fields: Whether to create fields for all model fields automatically.
        """
        if model is Undefined:  # Early return for the ModelGQLType class itself.
            return super().__new__(cls, __name, __bases, __attrs)

        if isinstance(model, type) and not issubclass(model, models.Model):
            msg = (
                "When subclassing `ModelGQLType`, you need to provide the model class as a keyword argument "
                "to the class definition, e.g. `class MyNode(ModelGQLType, model=MyModel)`."
            )
            raise TypeError(msg)

        if create_fields:
            cls._create_fields(model, __attrs, exclude)

        node = super().__new__(cls, __name, __bases, __attrs)

        if register:
            cls._register_node(model, node)  # type: ignore[arg-type]

        # ModelGQLType members should use '__dunder__' names to avoid name collisions with possible field names.
        node.__model__ = model
        node.__node_name__ = name or node.__name__
        node.__lookup_field__ = cls._get_lookup_field(model, lookup_field)
        return node

    @classmethod
    def _create_fields(cls, model: type[models.Model], attrs: dict[str, Any], exclude: Collection[str]) -> None:
        """Creates fields for all model fields, except those in exclude or already defined in the class."""
        for field in model._meta._get_fields():  # noqa: SLF001
            field_name = field.name

            if undine_settings.USE_PK_FIELD_NAME and getattr(field, "primary_key", False):
                field_name = "pk"

            if field_name in exclude or field_name in attrs:
                continue

            many = field.many_to_many or field.one_to_many
            nullable = getattr(field, "null", False)
            description = getattr(field, "help_text", None)
            # TODO: Deprecation reason.
            attrs[field_name] = Field(field, description=description, many=many, nullable=nullable)

    @classmethod
    def _register_node(cls, model: type[models.Model], node: type[ModelGQLType]) -> None:
        """Registers the created node in the node registry for the given model."""
        if model in cls.node_registry:
            node = cls.node_registry[model]
            msg = (
                f"A ModelGQLType for model '{dotpath(model)}' "
                f"has already been registered: '{dotpath(node)}'. "
                f"Use a proxy model or disable registration with "
                f"`class MyNode(ModelGQLType, model=MyModel, register=False)`."
            )
            raise ValueError(msg)

        cls.node_registry[model] = node  # type: ignore[assignment]

    @classmethod
    def _get_lookup_field(cls, model: type[models.Model], lookup_field: str) -> models.Field:
        if lookup_field == "pk":
            return model._meta.pk
        try:
            return model._meta.get_field(lookup_field)
        except FieldDoesNotExist as error:
            msg = f"Field '{lookup_field}' does not exist in model '{dotpath(model)}'."
            raise ValueError(msg) from error


class ModelGQLType(metaclass=ModelGQLTypeMeta, model=Undefined):
    """Base class for all GraphQL nodes backing a Django model."""

    # ModelGQLType members should use `__dunder__` names to avoid name collisions with possible field names.

    @classmethod
    def __get_queryset__(cls, info: GraphQLResolveInfo) -> models.QuerySet:
        """Get the base queryset for this ModelGQLType."""
        return cls.__model__._default_manager.get_queryset()

    @classmethod
    def __filter_queryset__(cls, queryset: models.QuerySet, info: GraphQLResolveInfo) -> models.QuerySet:
        """Filter the results of the queryset."""
        return queryset

    @classmethod
    def __resolve_one__(cls, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        """Top-level resolver for fetching a single model object."""
        with handle_get_errors(cls.__model__, **kwargs):
            return cls.__get_queryset__(info).get(**kwargs)

    @classmethod
    def __resolve_many__(cls, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        """Top-level resolver for fetching multiple model objects."""
        return cls.__get_queryset__(info)

    @classmethod
    def __get_filters__(cls) -> list[Any]:
        # TODO: Filters.
        return []

    @classmethod
    def __get_object_type__(cls) -> GraphQLObjectType:
        # Cache created type so that multiple fields can reuse it.
        # GraphQL schema cannot contain multiple types with the same name.
        if not hasattr(cls, "__object_type__"):
            cls.__object_type__ = GraphQLObjectType(
                name=cls.__node_name__,
                # Give fields as a callable to delay their creation.
                # This gives time for all ModelGQLTypes to be registered.
                fields=cls.__get_fields__,
                description=cls.__doc__,
                is_type_of=None,  # TODO: Implement.
                extensions={
                    "model_node": cls,
                },
            )
        return cls.__object_type__

    @classmethod
    def __get_fields__(cls) -> dict[str, GraphQLField]:
        # Cache field creation for performance.
        if not hasattr(cls, "__fields__"):
            cls.__fields__ = get_fields_from_class(cls)
        return cls.__fields__


@dataclass
class DeferredModelGQLType:
    """Represents a lazily evaluated ModelGQLType for a related field."""

    get_type: Callable[[], type[ModelGQLType]]
    name: str
    description: str | None
    required: bool
    many: bool
    model: type[models.Model]

    @classmethod
    def for_related_field(cls, field: ToOneField | ToManyField | GenericRelation | GenericRel) -> DeferredModelGQLType:
        name = field.name
        description = getattr(field, "help_text", None)
        required = field.null is False
        many = field.many_to_many or field.one_to_many
        model = field.related_model

        def inner() -> type[ModelGQLType]:
            value = ModelGQLTypeMeta.node_registry.get(model)
            if value is None:
                msg = f"ModelGQLType for field '{name}' of type '{dotpath(model)}' does not exist."
                raise ValueError(msg)

            return value

        return cls(get_type=inner, name=name, description=description, required=required, many=many, model=model)


@dataclass
class DeferredModelGQLTypeUnion:
    """Represents a lazily evaluated ModelGQLType for a related field."""

    get_types: Callable[[], list[type[ModelGQLType]]]
    name: str
    description: str | None
    model: type[models.Model]

    @classmethod
    def for_generic_foreign_key(cls, field: GenericForeignKey) -> DeferredModelGQLTypeUnion:
        from django.contrib.contenttypes.fields import GenericRelation

        name = field.name
        model = field.model
        deferred_types = [
            DeferredModelGQLType.for_related_field(f.remote_field)
            for f in model._meta._relation_tree  # noqa: SLF001
            if isinstance(f, GenericRelation)
        ]

        def inner() -> list[type[ModelGQLType]]:
            nonlocal deferred_types
            return [deferred_type.get_type() for deferred_type in deferred_types]

        return cls(get_types=inner, name=name, description="", model=model)
