from __future__ import annotations

from typing import TYPE_CHECKING, Any, Container, Iterable, Self

from graphql import (
    GraphQLBoolean,
    GraphQLField,
    GraphQLFieldResolver,
    GraphQLInputField,
    GraphQLInputType,
    GraphQLNonNull,
    GraphQLOutputType,
    Undefined,
)

from undine.converters import (
    convert_to_default_value,
    convert_to_graphql_type,
    convert_to_input_ref,
    is_input_hidden,
    is_input_only,
    is_input_required,
    is_many,
)
from undine.errors.exceptions import MissingModelError
from undine.middleware import (
    AtomicMutationMiddleware,
    InputDataModificationMiddleware,
    InputDataValidationMiddleware,
    InputOnlyDataRemovalMiddleware,
    IntegrityErrorHandlingMiddleware,
    MutationMiddleware,
    PostMutationHandlingMiddleware,
)
from undine.parsers import parse_description
from undine.registies import QUERY_TYPE_REGISTRY
from undine.settings import undine_settings
from undine.utils.graphql import get_or_create_input_object_type, get_or_create_object_type, maybe_list_or_non_null
from undine.utils.model_utils import get_lookup_field_name, get_model_field, get_model_fields_for_graphql
from undine.utils.reflection import FunctionEqualityWrapper, cache_signature_if_function, get_members, get_wrapped_func
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from django.db import models

    from undine.typing import GQLInfo, MutationKind, Root, ValidatorFunc

__all__ = [
    "Input",
    "MutationType",
]


class MutationTypeMeta(type):
    """A metaclass that modifies how a `MutationType` is created."""

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        *,
        # See `MutationType` for documentation of arguments.
        model: type[models.Model] | None = None,
        mutation_kind: MutationKind | None = None,
        auto: bool = True,
        exclude: Iterable[str] = (),
        typename: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> MutationTypeMeta:
        if model is Undefined:  # Early return for the `MutationType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if model is None:
            raise MissingModelError(name=_name, cls="MutationType")

        if mutation_kind is None:
            if callable(_attrs.get("__mutate__")):
                mutation_kind: MutationKind = "custom"
            elif "create" in _name.lower():
                mutation_kind: MutationKind = "create"
            elif "update" in _name.lower():
                mutation_kind: MutationKind = "update"
            elif "delete" in _name.lower():
                mutation_kind: MutationKind = "delete"
            else:
                mutation_kind: MutationKind = "custom"

        lookup_field = get_lookup_field_name(model)

        if lookup_field not in _attrs and mutation_kind in {"update", "delete"}:
            field = get_model_field(model=model, lookup=lookup_field)
            _attrs[lookup_field] = Input(field, required=True)

        if auto and mutation_kind != "delete":
            exclude = set(exclude) | set(_attrs)
            if mutation_kind == "create":
                exclude.add(lookup_field)
            _attrs |= get_inputs_for_model(model, exclude=exclude)

        # Add to attrs things that need to be available during `Input.__set_name__`.
        _attrs["__model__"] = model
        _attrs["__mutation_kind__"] = mutation_kind
        instance: type[MutationType] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        # Members should use `__dunder__` names to avoid name collisions with possible `undine.Input` names.
        instance.__model__ = model
        instance.__input_map__ = dict(get_members(instance, Input))
        instance.__lookup_field__ = lookup_field
        instance.__mutation_kind__ = mutation_kind
        instance.__typename__ = typename or _name
        instance.__extensions__ = (extensions or {}) | {undine_settings.MUTATION_EXTENSIONS_KEY: instance}
        return instance


class MutationType(metaclass=MutationTypeMeta, model=Undefined):
    """
    A class for creating a 'GraphQLInputObjectType' for a Django model.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this `MutationType` is for. This input is required.
    - `mutation_kind`: Kind of mutation this is. Can be "create", "update", or "delete" or "custom".
                       If not given, it will be guessed based on the name of the class.
    - `auto`: Whether to add inputs for all model fields automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from automatically added inputs. No excludes by default.
    - `typename`: Override name for the InputObjectType in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created `InputObjectType`. Defaults to `None`.

    >>> class MyMutationType(MutationType, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `undine.Input` names.

    @classmethod
    def __mutate__(cls, root: Root, info: GQLInfo, input_data: dict[str, Any]) -> Any:
        """Override this method for custom mutations."""

    @classmethod
    def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
        """Validate all input data given to this MutationType."""

    @classmethod
    def __post_handle__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
        """Post handling after the mutation is done."""

    @classmethod
    def __input_type__(cls) -> GraphQLInputType:
        """
        Create a `GraphQLInputObjectType` for this class.
        Cache the result since a GraphQL schema cannot contain multiple types with the same name.
        """
        if cls.__mutation_kind__ == "delete":
            input_field = cls.__input_map__.get(cls.__lookup_field__)
            return input_field.get_field_type()

        # Defer creating fields so that self-referential related inputs can be created.
        def fields() -> dict[str, GraphQLInputField]:
            fields_: dict[str, GraphQLInputField] = {}
            for name, inpt in cls.__input_map__.items():
                if inpt.hidden:
                    continue
                fields_[to_schema_name(name)] = inpt.as_graphql_input_field()
            return fields_

        return get_or_create_input_object_type(
            name=cls.__typename__,
            fields=FunctionEqualityWrapper(fields, context=cls),
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )

    @classmethod
    def __output_type__(cls) -> GraphQLOutputType:
        """Create a `GraphQLObjectType` for this class."""
        if cls.__mutation_kind__ == "delete":
            return get_or_create_object_type(
                name="DeleteMutationOutput",
                fields={
                    undine_settings.DELETE_MUTATION_OUTPUT_FIELD_NAME: GraphQLField(GraphQLNonNull(GraphQLBoolean)),
                },
            )
        return QUERY_TYPE_REGISTRY[cls.__model__].__output_type__()

    @classmethod
    def __middleware__(cls) -> list[type[MutationMiddleware]]:
        """Middleware to use with mutations with using this MutationType."""
        return [
            InputDataModificationMiddleware,
            InputDataValidationMiddleware,
            PostMutationHandlingMiddleware,
            InputOnlyDataRemovalMiddleware,
            IntegrityErrorHandlingMiddleware,
            AtomicMutationMiddleware,
        ]


class Input:
    def __init__(  # noqa: PLR0913
        self,
        ref: Any = None,
        *,
        many: bool = Undefined,
        required: bool = Undefined,
        default_value: Any = Undefined,
        input_only: bool = Undefined,
        hidden: bool = Undefined,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a `GraphQLInputField` in the `GraphQLInputObjectType` of a `MutationType`.
        In other words, it's an input used in the mutation of the `MutationType` it belongs to.

        :param ref: Reference to build the input from. Can be anything that `convert_to_input_ref` can convert,
                    e.g., a string referencing a model field name, a model field, a `MutationType`, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `MutationType` class.
        :param many: Whether the input should contain a non-null list of the referenced type.
                     If not provided, looks at the reference and tries to determine this from it.
        :param required: Whether the input should be required. If not provided, looks at the reference
                         and the MutationType's mutation kind to determine this.
        :param default_value: Value to use for the input if non is provided. Also makes the input not required,
                              if not otherwise specified. Must be a valid GraphQL default value.
        :param input_only: If `True`, the input's value is not included when the mutation is performed
                           (value still exists for any mutation middlewares). If not provided,
                           looks at the reference, and if it doesn't point to a field on the model,
                           this field will be considered input-only.
        :param hidden: If `True`, the input is not included in the schema. In most cases, should also
                       add a `default_value` for the input.
        :param description: Description for the input. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the input is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the input.
        """
        self.ref = cache_signature_if_function(ref, depth=1)
        self.many = many
        self.required = required
        self.input_only = input_only
        self.hidden = hidden
        self.default_value = default_value
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.validator_func: ValidatorFunc | None = None
        self.extensions = extensions or {}
        self.extensions[undine_settings.INPUT_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[MutationType], name: str) -> None:
        self.owner = owner
        self.name = name
        self.ref = convert_to_input_ref(self.ref, caller=self)

        if self.many is Undefined:
            self.many = is_many(self.ref, model=self.owner.__model__, name=self.name)
        if self.input_only is Undefined:
            self.input_only = is_input_only(self.ref)
        if self.hidden is Undefined:
            self.hidden = is_input_hidden(self.ref)
        if self.default_value is Undefined:
            self.default_value = convert_to_default_value(self.ref)
        if self.required is Undefined:
            self.required = is_input_required(self.ref, caller=self)
        if self.description is Undefined:
            self.description = parse_description(self.ref)

    def __call__(self, ref: GraphQLFieldResolver, /) -> Self:
        """Called when using as decorator with parenthesis: @Input(...)"""
        self.ref = cache_signature_if_function(ref, depth=1)
        return self

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref})>"

    def as_graphql_input_field(self) -> GraphQLInputField:
        return GraphQLInputField(
            type_=self.get_field_type(),
            default_value=self.default_value,
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            out_name=self.name,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLInputType:
        graphql_type = convert_to_graphql_type(self.ref, model=self.owner.__model__, is_input=True)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=self.required)

    def validate(self, func: ValidatorFunc = None, /) -> ValidatorFunc:
        """Decorate a function to add validation for this input."""
        if func is None:  # Allow `@<input_name>.validator()`
            return self.validate  # type: ignore[return-value]
        self.validator_func = get_wrapped_func(func)
        return func


def get_inputs_for_model(model: type[models.Model], *, exclude: Container[str]) -> dict[str, Input]:
    """Add undine.Inputs for all of the given model's fields, except those in the 'exclude' list."""
    result: dict[str, Input] = {}
    for model_field in get_model_fields_for_graphql(model, include_nonsaveable=False):
        field_name = model_field.name

        is_primary_key = bool(getattr(model_field, "primary_key", False))

        if is_primary_key:
            field_name = get_lookup_field_name(model)

        if field_name in exclude:
            continue

        result[field_name] = Input(model_field)

    return result
