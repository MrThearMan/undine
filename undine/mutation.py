from __future__ import annotations

from collections import deque
from types import FunctionType
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Generic, Unpack

from graphql import DirectiveLocation, GraphQLError, GraphQLInputField, Undefined

from undine.converters import (
    convert_to_default_value,
    convert_to_description,
    convert_to_graphql_type,
    convert_to_input_ref,
    is_input_hidden,
    is_input_only,
    is_input_required,
    is_many,
)
from undine.dataclasses import MaybeManyOrNonNull
from undine.exceptions import GraphQLErrorGroup, MissingModelGenericError
from undine.parsers import parse_class_attribute_docstrings
from undine.query import QUERY_TYPE_REGISTRY
from undine.settings import undine_settings
from undine.typing import JsonObject, MutationKind, TModel
from undine.utils.graphql.type_registry import (
    get_or_create_graphql_input_object_type,
    get_or_create_graphql_object_type,
)
from undine.utils.graphql.utils import check_directives, with_graphql_error_path
from undine.utils.model_utils import get_model_field, get_model_fields_for_graphql
from undine.utils.reflection import FunctionEqualityWrapper, cache_signature_if_function, get_members, get_wrapped_func
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Container

    from django.db.models import Model
    from graphql import GraphQLFieldResolver, GraphQLInputObjectType, GraphQLInputType, GraphQLObjectType

    from undine import QueryType
    from undine.directives import Directive
    from undine.typing import (
        DefaultValueType,
        GQLInfo,
        InputParams,
        InputPermFunc,
        MutationTypeParams,
        PermissionFunc,
        ValidatorFunc,
    )

__all__ = [
    "Input",
    "MutationType",
]


class MutationTypeMeta(type):
    """A metaclass that modifies how a `MutationType` is created."""

    # Set in '__new__'
    __model__: type[Model]
    __input_map__: dict[str, Input]
    __kind__: MutationKind
    __schema_name__: str
    __directives__: list[Directive]
    __extensions__: dict[str, Any]
    __attribute_docstrings__: dict[str, str]

    # Stores the models from generics so that they can be accesses in '__new__'
    __model_deque__: deque[type[Model]] = deque()

    def __new__(  # noqa: PLR0912, C901
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        **kwargs: Unpack[MutationTypeParams],
    ) -> MutationTypeMeta:
        if _name == "MutationType":  # Early return for the `MutationType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        try:
            model = MutationTypeMeta.__model__
            del MutationTypeMeta.__model__
        except AttributeError as error:
            raise MissingModelGenericError(name=_name, cls="MutationType") from error

        kind = kwargs.get("kind")
        if kind is None:
            if callable(_attrs.get("__mutate__")):
                mutation_kind = MutationKind.custom
            elif "create" in _name.lower():
                mutation_kind = MutationKind.create
            elif "update" in _name.lower():
                mutation_kind = MutationKind.update
            elif "delete" in _name.lower():
                mutation_kind = MutationKind.delete
            elif "related" in _name.lower():
                mutation_kind = MutationKind.related
            else:
                mutation_kind = MutationKind.custom
        else:
            mutation_kind = MutationKind(kind)

        if "pk" not in _attrs and mutation_kind.requires_pk:
            field = get_model_field(model=model, lookup="pk")
            _attrs["pk"] = Input(field, required=True)

        auto = kwargs.get("auto", True)
        exclude = set(kwargs.get("exclude", []))
        if auto and mutation_kind.should_use_auto:
            exclude |= set(_attrs)
            if mutation_kind.no_pk:
                exclude.add("pk")
            _attrs |= get_inputs_for_model(model, exclude=exclude)

        mutation_type = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `Input` names.
        mutation_type.__model__ = model
        mutation_type.__input_map__ = get_members(mutation_type, Input)
        mutation_type.__kind__ = mutation_kind
        mutation_type.__schema_name__ = kwargs.get("schema_name", _name)
        mutation_type.__directives__ = kwargs.get("directives", [])
        mutation_type.__extensions__ = kwargs.get("extensions", {})
        mutation_type.__attribute_docstrings__ = parse_class_attribute_docstrings(mutation_type)

        check_directives(mutation_type.__directives__, location=DirectiveLocation.INPUT_OBJECT)
        mutation_type.__extensions__[undine_settings.MUTATION_TYPE_EXTENSIONS_KEY] = mutation_type

        for name, input_ in mutation_type.__input_map__.items():
            input_.__connect__(mutation_type, name)  # type: ignore[arg-type]

        return mutation_type

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_input_object_type(cls.__input_type__())

    def __getitem__(cls, model: type[TModel]) -> type[MutationType[TModel]]:
        # Note that this should be cleaned up in '__new__',
        # but is not if an error occurs in the class body of the defined 'MutationType'!
        MutationTypeMeta.__model__ = model
        return cls  # type: ignore[return-value]

    def __input_type__(cls) -> GraphQLInputObjectType:
        """Create the `GraphQLInputObjectType` for this `MutationType`."""
        return get_or_create_graphql_input_object_type(
            name=cls.__schema_name__,
            fields=FunctionEqualityWrapper(cls.__input_fields__, context=cls),
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )

    def __input_fields__(cls) -> dict[str, GraphQLInputField]:
        """Defer creating fields so that self-referential related inputs can be created."""
        return {
            input_.schema_name: input_.as_graphql_input_field()
            for input_ in cls.__input_map__.values()
            if not input_.hidden
        }

    def __query_type__(cls) -> type[QueryType]:
        """Get the `QueryType` for this `MutationType`."""
        return QUERY_TYPE_REGISTRY[cls.__model__]

    def __output_type__(cls) -> GraphQLObjectType:
        """Create the GraphQL `ObjectType` for this `MutationType`."""
        query_type = cls.__query_type__()

        if cls.__kind__ == MutationKind.delete:
            field = query_type.__field_map__["pk"]
            return get_or_create_graphql_object_type(
                name=cls.__schema_name__ + "Output",
                fields={"pk": field.as_graphql_field()},
            )

        return query_type.__output_type__()


class MutationType(Generic[TModel], metaclass=MutationTypeMeta):
    """
    A class for creating a mutation in the GraphQL schema based on a Django Model.

    Must set the Django Model this `MutationType` is for using the generic type argument.

    The following parameters can be passed in the class definition:

    `kind: Literal["create", "update", "delete", "custom", "related"] = <inferred>`
        The kind of mutation this is. If not given, use "custom" if `__mutate__` is defined,
        or infer based on the name of the class.

    `auto: bool = True`
        Whether to add `Input` attributes for all Model fields automatically.

    `exclude: list[str] = []`
        Model fields to exclude from automatically added `Input` attributes.

    `schema_name: str = <class name>`
        Override name for the `InputObjectType` for this `MutationType` in the GraphQL schema.

    `directives: list[Directive] = []`
        `Directives` to add to the created `InputObjectType`.

    `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `InputObjectType`.

    >>> class CreateTaskMutation(MutationType[Task]): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `Input` names.

    # Set in metaclass
    __model__: ClassVar[type[Model]]
    __input_map__: ClassVar[dict[str, Input]]
    __kind__: ClassVar[MutationKind]
    __schema_name__: ClassVar[str]
    __directives__: ClassVar[list[Directive]]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]

    @classmethod
    def __mutate__(cls, root: Any, info: GQLInfo, input_data: Annotated[Any, JsonObject]) -> Any:
        """Override this method for custom mutations."""

    @classmethod
    def __permissions__(cls, instance: TModel, info: GQLInfo, input_data: dict[str, Any]) -> None:
        """Check permissions for a mutation using this `MutationType`."""

    @classmethod
    def __validate__(cls, instance: TModel, info: GQLInfo, input_data: dict[str, Any]) -> None:
        """Validate all input data given to this `MutationType`."""

    @classmethod
    def __after__(cls, instance: TModel, info: GQLInfo, previous_data: dict[str, Any]) -> None:
        """A function that is run after a mutation using this `MutationType` has been executed."""

    @classmethod
    def __before__(cls, instance: TModel, info: GQLInfo, input_data: dict[str, Any]) -> None:
        """A function that is run before a mutation using this `MutationType` is executed."""
        to_remove: list[str] = []

        with with_graphql_error_path(info):
            cls.__permissions__(instance, info, input_data)

        errors: list[GraphQLError] = []

        for input_field in cls.__input_map__.values():
            try:
                input_field.before(instance, info, input_data)
            except GraphQLError as error:
                errors.append(error)
                continue

            if input_field.input_only and input_field.name in input_data:
                to_remove.append(input_field.name)

        if errors:
            raise GraphQLErrorGroup(errors)

        with with_graphql_error_path(info):
            cls.__validate__(instance, info, input_data)

        for field_name in to_remove:
            input_data.pop(field_name, None)


class Input:
    """
    A class for defining a possible input for a mutation.
    Represents an input field on a GraphQL `InputObjectType` for the `MutationType` this is added to.

    >>> class CreateTaskMutation(MutationType[Task]):
    ...     name = Input()
    """

    def __init__(self, ref: Any = None, **kwargs: Unpack[InputParams]) -> None:
        """
        Create a new Input.

        :param ref: Reference to build the input from. Must be convertable by the `convert_to_input_ref` function.
                    If not provided, use the name of the attribute this is assigned to in the `MutationType` class.
        :param many: Whether the `Input` should return a non-null list of the referenced type.
        :param required: Whether the input should be required.
        :param default_value: Value to use for the input if none is provided. Also makes the input not required,
                              if not otherwise specified. Must be a valid GraphQL default value.
        :param input_only: If `True`, the value for this `Input` is not included when the mutation is performed,
                           but is still available during permission checks and validation.
        :param hidden: If `True`, the `Input` is not included in the schema. In most cases, should also
                       add a `default_value` for the input.
        :param description: Description for the input.
        :param deprecation_reason: If the `Input` is deprecated, describes the reason for deprecation.
        :param field_name: Name of the field in the Django model. If not provided, use the name of the attribute.
        :param schema_name: Actual name of the `Input` in the GraphQL schema. Can be used to alias the `Input`
                            for the schema, or when the desired name is a Python keyword (e.g. `if` or `from`).
        :param directives: GraphQL directives for the `Input`.
        :param extensions: GraphQL extensions for the `Input`.
        """
        self.ref: Any = cache_signature_if_function(ref, depth=1)

        self.many: bool = kwargs.get("many", Undefined)  # type: ignore[assignment]
        self.required: bool = kwargs.get("required", Undefined)  # type: ignore[assignment]
        self.input_only: bool = kwargs.get("input_only", Undefined)  # type: ignore[assignment]
        self.hidden: bool = kwargs.get("hidden", Undefined)  # type: ignore[assignment]
        self.default_value: DefaultValueType = kwargs.get("default_value", Undefined)
        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.field_name: str = kwargs.get("field_name", Undefined)  # type: ignore[assignment]
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]
        self.directives: list[Directive] = kwargs.get("directives", [])
        self.extensions: dict[str, Any] = kwargs.get("extensions", {})

        check_directives(self.directives, location=DirectiveLocation.INPUT_FIELD_DEFINITION)
        self.extensions[undine_settings.INPUT_EXTENSIONS_KEY] = self

        self.validator_func: ValidatorFunc | None = None
        self.permissions_func: PermissionFunc | None = None

    def __connect__(self, mutation_type: type[MutationType], name: str) -> None:
        """Connect this `Input` to the given `MutationType` using the given name."""
        self.mutation_type = mutation_type
        self.name = name
        self.field_name = self.field_name or name
        self.schema_name = self.schema_name or to_schema_name(name)

        if isinstance(self.ref, str):
            self.field_name = self.ref

        self.ref = convert_to_input_ref(self.ref, caller=self)

        if self.many is Undefined:
            self.many = is_many(self.ref, model=self.mutation_type.__model__, name=self.field_name)
        if self.input_only is Undefined:
            self.input_only = is_input_only(self.ref, caller=self)
        if self.hidden is Undefined:
            self.hidden = is_input_hidden(self.ref, caller=self)
        if self.default_value is Undefined and self.mutation_type.__kind__.should_include_default_value:
            self.default_value = convert_to_default_value(self.ref)
        if self.required is Undefined:
            self.required = is_input_required(self.ref, caller=self)
        if self.description is Undefined:
            self.description = self.mutation_type.__attribute_docstrings__.get(name)
            if self.description is None:
                self.description = convert_to_description(self.ref)

    def __call__(self, ref: GraphQLFieldResolver, /) -> Input:
        """Called when using as decorator with parenthesis: @Input(...)"""
        self.ref = cache_signature_if_function(ref, depth=1)
        return self

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref!r})>"

    def __str__(self) -> str:
        inpt = self.as_graphql_input_field()
        return undine_settings.SDL_PRINTER.print_input_field(self.schema_name, inpt, indent=False)

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
        value = MaybeManyOrNonNull(self.ref, many=self.many, nullable=not self.required)
        return convert_to_graphql_type(value, model=self.mutation_type.__model__, is_input=True)  # type: ignore[return-value]

    def validate(self, func: ValidatorFunc | None = None, /) -> ValidatorFunc:
        """Decorate a function to add validation for this input."""
        if func is None:  # Allow `@<input_name>.validate()`
            return self.validate
        self.validator_func = get_wrapped_func(func)
        return func

    def permissions(self, func: InputPermFunc | None = None, /) -> InputPermFunc:
        """Decorate a function to add it as a permission check for this input."""
        if func is None:  # Allow `@<input_name>.permissions()`
            return self.permissions
        self.permissions_func = get_wrapped_func(func)
        return func

    def before(self, instance: Model, info: GQLInfo, input_data: dict[str, Any]) -> None:
        """Input checks to run before mutation."""
        if self.hidden:
            if isinstance(self.ref, FunctionType):
                input_data[self.name] = self.ref(instance, info)

            elif self.default_value is not Undefined:
                input_data[self.name] = self.default_value

        value: Any = input_data.get(self.name, Undefined)
        if value is Undefined:
            return

        if not self.hidden and isinstance(self.ref, FunctionType):
            input_data[self.name] = value = self.ref(instance, info, value)

        # Only check permissions and do validation if value is not the default value.
        if value == self.default_value:
            return

        with with_graphql_error_path(info, key=self.name):
            if self.permissions_func is not None:
                self.permissions_func(instance, info, value)

            if self.validator_func is not None:
                self.validator_func(instance, info, value)


def get_inputs_for_model(model: type[Model], *, exclude: Container[str] = ()) -> dict[str, Input]:
    """Add `Inputs` for all the given model's fields, except those in the 'exclude' list."""
    from django.contrib.contenttypes.fields import GenericForeignKey  # noqa: PLC0415

    result: dict[str, Input] = {}

    remove_inputs: set[str] = set()

    for model_field in get_model_fields_for_graphql(model, exclude_nonsaveable=True):
        field_name = model_field.name

        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if is_primary_key:
            field_name = "pk"

        # If a 'GenericForeignKey' is added, don't include the 'content type'
        # and 'object ID' inputs, see 'GenericForeignKey' docs in Django.
        if isinstance(model_field, GenericForeignKey):
            remove_inputs.add(model_field.ct_field)
            remove_inputs.add(model_field.fk_field)

        if field_name in exclude:
            continue

        result[field_name] = Input(model_field)

    for field_name in remove_inputs:
        result.pop(field_name, None)

    return result
