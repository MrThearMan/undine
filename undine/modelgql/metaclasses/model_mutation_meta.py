from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from graphql import GraphQLInputObjectType, GraphQLObjectType, Undefined

from undine.errors import MissingModelError, MissingOutputTypeError
from undine.fields import Input, get_inputs_for_model
from undine.parsers import parse_model_field
from undine.settings import undine_settings
from undine.utils.decorators import cached_class_property
from undine.utils.delete_output_type import DeleteMutationOutputType
from undine.utils.mutation_handler import MutationHandler
from undine.utils.reflection import get_members
from undine.utils.registry import TYPE_REGISTRY
from undine.utils.text import get_docstring, get_schema_name

if TYPE_CHECKING:
    from django.db import models

    from undine.modelgql.model_mutation import ModelGQLMutation
    from undine.modelgql.model_type import ModelGQLType
    from undine.typing import MutationKind


__all__ = [
    "ModelGQLMutationMeta",
]


class ModelGQLMutationMeta(type):
    """A metaclass that modifies how a `ModelGQLMutation` is created."""

    def __new__(  # noqa: PLR0913
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        mutation_kind: MutationKind | None = None,
        output_type: type[ModelGQLType] | GraphQLObjectType | None = None,
        auto_inputs: bool = False,
        exclude: Iterable[str] = (),
        lookup_field: str = "pk",
        name: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelGQLMutationMeta:
        """See `ModelGQLMutation` for documentation of arguments."""
        if model is Undefined:  # Early return for the `ModelGQLMutation` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if model is None:
            raise MissingModelError(name=_name, cls="ModelGQLMutation")

        if mutation_kind is None:
            if "create" in _name.lower():
                mutation_kind = "create"
            elif "update" in _name.lower():
                mutation_kind = "update"
            elif "delete" in _name.lower():
                mutation_kind = "delete"
            else:
                mutation_kind = "custom"

        if mutation_kind == "delete" and output_type is None:
            output_type = DeleteMutationOutputType

        if lookup_field not in _attrs and mutation_kind in ["create", "update"]:
            field = parse_model_field(model=model, lookup=lookup_field)
            _attrs[lookup_field] = Input(field, required=True)

        if auto_inputs:
            _attrs |= get_inputs_for_model(model, exclude=set(exclude) | set(_attrs))

        # Add model to attrs before class creation so that it's available during `Input.__set_name__`.
        _attrs["__model__"] = model
        instance: type[ModelGQLMutation] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        # Members should use '__dunder__' names to avoid name collisions with possible filter names.
        instance.__model__ = model
        instance.__input_map__ = {get_schema_name(name): input_ for name, input_ in get_members(instance, Input)}
        instance.__lookup_field__ = lookup_field
        instance.__mutation_kind__ = mutation_kind
        instance.__mutation_handler__ = MutationHandler(instance)
        instance.__output_type__ = output_type or get_output_object_type_for_model_mutation()
        instance.__input_type__ = get_input_object_type_for_model_mutation(instance, name=name, extensions=extensions)
        return instance


def get_output_object_type_for_model_mutation() -> type[ModelGQLType]:
    @cached_class_property
    def wrapper(cls: type[ModelGQLMutation]) -> type[ModelGQLType]:
        output_type = TYPE_REGISTRY.get(cls.__model__)
        if output_type is None:
            raise MissingOutputTypeError(name=cls.__name__, cls="ModelGQLMutation")
        return output_type

    return wrapper  # type: ignore[return-value]


def get_input_object_type_for_model_mutation(
    instance: type[ModelGQLMutation],
    *,
    name: str | None = None,
    extensions: dict[str, Any] | None,
) -> GraphQLInputObjectType:
    """
    Create the InputObjectType argument for the given `ModelGQLMutation`

    `InputObjectType` should be created once, since GraphQL schema cannot
    contain multiple types with the same name.
    """
    if name is None:
        name = instance.__name__
    if extensions is None:
        extensions = {}

    return GraphQLInputObjectType(
        name=name,
        description=get_docstring(instance),
        # Defer creating fields so that self-referential related fields can be created.
        fields=lambda: {
            # Lookup field is always required.
            input_name: input_.as_input_field(required=input_name == instance.__lookup_field__)
            for input_name, input_ in instance.__input_map__.items()
        },
        extensions={
            **extensions,
            undine_settings.MUTATION_INPUT_EXTENSIONS_KEY: instance,
        },
    )
