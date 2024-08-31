from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models, transaction
from graphql import GraphQLResolveInfo, Undefined

from undine import error_codes
from undine.errors import GraphQLStatusError
from undine.utils.error_helpers import handle_integrity_errors
from undine.utils.text import dotpath

from .metaclasses.model_mutation_meta import ModelGQLMutationMeta

if TYPE_CHECKING:
    from undine.typing import Root


class ModelGQLMutation(metaclass=ModelGQLMutationMeta, model=Undefined):
    """
    Base class for creating mutations for a Django model.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this `ModelGQLMutation` is for. This input is required.
    - `output_type`: Output `ModelGQLType` for this mutation. By default, use the registered
                    `ModelGQLType` for the given model.
    - `auto_inputs`: Whether to add inputs for all model fields automatically. Defaults to `False`.
    - `exclude`: List of model fields to exclude from automatically added inputs. No excludes by default.
    - `lookup_field`: Name of the field to use for looking up single objects. Use "pk" by default.
    - `name`: Override name for the InputObjectType in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created `InputObjectType`. Defaults to `None`.

    >>> class MyMutation(ModelGQLMutation, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible ordering field names.

    @classmethod
    def __create_mutation__(cls, root: Root, info: GraphQLResolveInfo, input_data: dict[str, Any]) -> models.Model:
        cls.__validate_create__(info, input_data)
        with transaction.atomic(), handle_integrity_errors():
            return cls.__mutation_handler__.create(input_data)

    @classmethod
    def __update_mutation__(cls, root: Root, info: GraphQLResolveInfo, input_data: dict[str, Any]) -> models.Model:
        instance = cls.__get_instance__(input_data)
        cls.__validate_update__(instance, info, input_data)
        with transaction.atomic(), handle_integrity_errors():
            return cls.__mutation_handler__.update(instance, input_data)

    @classmethod
    def __delete_mutation__(cls, root: Root, info: GraphQLResolveInfo, input_data: dict[str, Any]) -> Any:
        instance = cls.__get_instance__(input_data)
        cls.__validate_delete__(instance, info)
        with handle_integrity_errors():
            instance.delete()
        return {"success": True}

    @classmethod
    def __custom_mutation__(cls, root: Root, info: GraphQLResolveInfo, input_data: dict[str, Any]) -> Any:
        """Override this method for custom mutations."""

    @classmethod
    def __validate_create__(cls, info: GraphQLResolveInfo, input_data: dict[str, Any]) -> None:
        """Implement to perform additional validation before the given instance is created."""

    @classmethod
    def __validate_update__(cls, instance: models.Model, info: GraphQLResolveInfo, input_data: dict[str, Any]) -> None:
        """Implement to perform additional validation before the given instance is updates."""

    @classmethod
    def __validate_delete__(cls, instance: models.Model, info: GraphQLResolveInfo) -> None:
        """Implement to perform additional validation before the given instance is deleted."""

    @classmethod
    def __get_instance__(cls, input_data: dict[str, Any]) -> models.Model:
        key = cls.__lookup_field__
        value = input_data.get(key, Undefined)
        if value is Undefined:
            msg = (
                f"Input data is missing value for the mutation lookup field {key!r}. "
                f"Cannot fetch `{dotpath(cls.__model__)}` object for mutation."
            )
            raise GraphQLStatusError(msg, status=500, code=error_codes.LOOKUP_VALUE_MISSING)

        return cls.__mutation_handler__.get(key=key, value=value)
