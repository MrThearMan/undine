from __future__ import annotations

from typing import TYPE_CHECKING, Any, Collection

from django.db import models
from graphql import GraphQLEnumType, GraphQLEnumValue, Undefined

from undine.errors import MissingModelError
from undine.fields import Ordering
from undine.settings import undine_settings
from undine.utils.reflection import get_members
from undine.utils.text import get_docstring, get_schema_name

if TYPE_CHECKING:
    from undine.modelgql.model_ordering import ModelGQLOrdering

__all__ = [
    "ModelGQLOrderingMeta",
]


class ModelGQLOrderingMeta(type):
    """A metaclass that modifies how a `ModelGQLOrdering` is created."""

    def __new__(  # noqa: PLR0913
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

        if models is None:
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

        for name, ordering_ in instance.__ordering_map__.items():
            if not ordering_.supports_reversing:
                enum_values[name] = GraphQLEnumValue(value=name, description=ordering_.description)
                continue

            for direction in ("Asc", "Desc"):
                schema_name = f"{name}{direction}"
                enum_values[schema_name] = GraphQLEnumValue(value=schema_name, description=ordering_.description)

        return enum_values
