from __future__ import annotations

from typing import TYPE_CHECKING, Any, Collection

from graphql import GraphQLInputField, GraphQLInputObjectType, Undefined

from undine.errors import MissingModelError
from undine.fields import Filter
from undine.settings import undine_settings
from undine.utils.reflection import get_members
from undine.utils.text import get_docstring, get_schema_name

if TYPE_CHECKING:
    from django.db import models

    from undine.modelgql.model_filter import ModelGQLFilter


__all__ = [
    "ModelGQLFilterMeta",
]


class ModelGQLFilterMeta(type):
    """A metaclass that modifies how a `ModelGQLFilter` is created."""

    def __new__(  # noqa: PLR0913
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

        if model is None:
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
        fields = {name: filter_.as_input_field() for name, filter_ in instance.__filter_map__.items()}
        fields["AND"] = fields["OR"] = fields["NOT"] = fields["XOR"] = GraphQLInputField(type_=iot)
        return fields
