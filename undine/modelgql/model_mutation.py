from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import GraphQLInputField, GraphQLInputObjectType, GraphQLObjectType, Undefined

from undine.utils.decorators import cached_class_method
from undine.utils.registry import TYPE_REGISTRY
from undine.utils.text import get_docstring

from .metaclasses.model_mutation_meta import DeleteMutationOutputType, ModelGQLMutationMeta

if TYPE_CHECKING:
    from django.db.models import Model

    from undine.typing import GQLInfo, Root


__all__ = [
    "ModelGQLMutation",
]


class ModelGQLMutation(metaclass=ModelGQLMutationMeta, model=Undefined):
    """
    Base class for creating mutations for a Django model.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this `ModelGQLMutation` is for. This input is required.
    - `mutation_kind`: Kind of mutation this is. Can be "create", "update", or "delete" or "custom".
                       If not given, it will be guessed based on the name of the class.
    - `auto_inputs`: Whether to add inputs for all model fields automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from automatically added inputs. No excludes by default.
    - `lookup_field`: Name of the field to use for looking up single objects. Use "pk" by default.
    - `name`: Override name for the InputObjectType in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created `InputObjectType`. Defaults to `None`.

    >>> class MyMutation(ModelGQLMutation, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible ordering field names.

    @classmethod
    def __mutate__(cls, root: Root, info: GQLInfo, input_data: dict[str, Any]) -> Any:
        """Override this method for custom mutations."""

    @classmethod
    def __pre_mutation__(cls, instance: Model | None, info: GQLInfo, input_data: dict[str, Any]) -> None:
        """
        Implement to perform additional actions before mutation happens.

        :param instance: The instance to be mutated. For create mutations, this will be `None`.
        :param info: The GraphQL resolve info.
        :param input_data: The input data for the mutation.
        """

    @classmethod
    def __post_mutation__(cls, instance: Model | None, info: GQLInfo, input_data: dict[str, Any]) -> None:
        """
        Implement to perform additional actions after mutation has happened.

        :param instance: The instance that was mutated. For delete mutations, this will be `None`.
        :param info: The GraphQL resolve info.
        :param input_data: The input data for the mutation.
        """

    @cached_class_method
    def __input_type__(cls) -> GraphQLInputObjectType:
        """
        Create a `GraphQLInputObjectType` for this class.
        Cache the result since a GraphQL schema cannot contain multiple types with the same name.
        """

        # Defer creating fields so that self-referential related fields can be created.
        def fields() -> dict[str, GraphQLInputField]:
            return {input_name: input_.as_graphql_input() for input_name, input_ in cls.__input_map__.items()}

        return GraphQLInputObjectType(
            name=cls.__typename__,
            fields=fields,
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )

    @cached_class_method
    def __output_type__(cls) -> GraphQLObjectType:
        """Create a `GraphQLObjectType` for this class."""
        if cls.__mutation_kind__ == "delete":
            return DeleteMutationOutputType
        return TYPE_REGISTRY[cls.__model__].__output_type__()
