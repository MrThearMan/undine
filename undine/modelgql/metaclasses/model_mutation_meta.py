from __future__ import annotations

from typing import TYPE_CHECKING, Any, Container, Iterable

from graphql import GraphQLBoolean, GraphQLField, GraphQLNonNull, GraphQLObjectType, Undefined

from undine.errors.exceptions import MissingModelError
from undine.fields import Input
from undine.settings import undine_settings
from undine.utils.model_utils import get_model_field
from undine.utils.mutation_handler import MutationHandler
from undine.utils.reflection import get_members
from undine.utils.text import get_schema_name

if TYPE_CHECKING:
    from django.db import models

    from undine.modelgql.model_mutation import ModelGQLMutation
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
        auto_inputs: bool = True,
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
                mutation_kind: MutationKind = "create"
            elif "update" in _name.lower():
                mutation_kind: MutationKind = "update"
            elif "delete" in _name.lower():
                mutation_kind: MutationKind = "delete"
            else:
                mutation_kind: MutationKind = "custom"

        if lookup_field not in _attrs and mutation_kind in ["update", "delete"]:
            field = get_model_field(model=model, lookup=lookup_field)
            _attrs[get_schema_name(lookup_field)] = Input(field, required=True)

        if auto_inputs:
            exclude = set(exclude) | set(_attrs)
            if mutation_kind == "create":
                exclude.add(lookup_field)
            _attrs |= get_inputs_for_model(model, exclude=exclude)

        # Add to attrs before class creation so that these are available during `Input.__set_name__`
        _attrs["__model__"] = model
        _attrs["__mutation_kind__"] = mutation_kind
        instance: type[ModelGQLMutation] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        # Members should use '__dunder__' names to avoid name collisions with possible filter names.
        instance.__model__ = model
        instance.__input_map__ = {get_schema_name(name): input_ for name, input_ in get_members(instance, Input)}
        instance.__lookup_field__ = lookup_field
        instance.__mutation_kind__ = mutation_kind
        instance.__mutation_handler__ = MutationHandler(instance)
        instance.__typename__ = name or _name
        instance.__extensions__ = extensions or {} | {undine_settings.MUTATION_INPUT_EXTENSIONS_KEY: cls}
        return instance


def get_inputs_for_model(model: type[models.Model], *, exclude: Container[str]) -> dict[str, Input]:
    """Add 'Input's for all of the given model's fields, except those in the 'exclude' list."""
    result: dict[str, Input] = {}
    for model_field in model._meta._get_fields():
        field_name = model_field.name
        is_primary_key = bool(getattr(model_field, "primary_key", False))
        editable = bool(getattr(model_field, "editable", True))

        if not editable:
            continue

        if is_primary_key and undine_settings.USE_PK_FIELD_NAME:
            field_name = "pk"

        if field_name in exclude:
            continue

        result[field_name] = Input(model_field)

    return result


DeleteMutationOutputType = GraphQLObjectType(
    name="DeleteMutationOutput",
    fields={"success": GraphQLField(GraphQLNonNull(GraphQLBoolean))},
)
