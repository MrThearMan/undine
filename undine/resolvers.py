"""
Contains different types of resolvers for GraphQL operations.
Resolvers must be callables with the following signature:

(root: Root, info: GQLInfo, **kwargs: Any) -> Any
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Self

from django.db import transaction
from graphql import GraphQLResolveInfo, Undefined

from undine.errors.error_handlers import handle_integrity_errors
from undine.errors.exceptions import GraphQLMissingLookupFieldError
from undine.settings import undine_settings
from undine.utils.model_utils import get_instance_or_raise
from undine.utils.reflection import get_signature, is_subclass

if TYPE_CHECKING:
    from types import FunctionType

    from django.db import models
    from django.db.models import Model

    from undine.mutation import MutationType
    from undine.typing import GQLInfo, RelatedManager, Root

__all__ = [
    "CreateResolver",
    "CustomResolver",
    "DeleteResolver",
    "FieldResolver",
    "ModelFieldResolver",
    "ModelManyRelatedResolver",
    "UpdateResolver",
]


@dataclass(frozen=True, slots=True)
class ModelFieldResolver:
    """Resolves a model field to a value by attribute access."""

    name: str

    def __call__(self, model: models.Model, info: GQLInfo, **kwargs: Any) -> Any:
        return getattr(model, self.name, None)


@dataclass(frozen=True, slots=True)
class ModelManyRelatedResolver:
    """Resolves a many-related model field as its queryset."""

    name: str

    def __call__(self, model: models.Model, info: GQLInfo, **kwargs: Any) -> Any:
        related_manager: RelatedManager = getattr(model, self.name)
        return related_manager.get_queryset()


@dataclass(frozen=True, slots=True)
class FieldResolver:
    """
    Resolves a GraphQL fields through an adapter layer from the 'GraphQLFieldResolver' signature
    into the given functions signature.
    """

    func: FunctionType | Callable[..., Any]
    root_param: str | None = None
    info_param: str | None = None

    @classmethod
    def from_func(cls, func: FunctionType, *, depth: int = 0) -> Self:
        """
        Create the appropriate FieldResolver for a function based on its signature.
        Leave out the `root` parameter from static functions, and only include the
        `info` parameter if the function has a parameter of the `GraphQLResolveInfo` type.

        Note that the `root` is always the first parameter, and the matching happens
        by it's name, which can be configured with `RESOLVER_ROOT_PARAM_NAME`.
        `self` and `cls` are always accepted root parameter names, since they are the
        conventions for instance and class methods respectively.
        """
        sig = get_signature(func, depth=depth + 1)

        root_param: str | None = None
        info_param: str | None = None
        for i, param in enumerate(sig.parameters.values()):
            if i == 0 and param.name in ("self", "cls", undine_settings.RESOLVER_ROOT_PARAM_NAME):
                root_param = param.name

            elif is_subclass(param.annotation, GraphQLResolveInfo):
                info_param = param.name
                break

        return cls(func=func, root_param=root_param, info_param=info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info
        return self.func(**kwargs)


@dataclass(frozen=True, slots=True)
class CreateResolver:
    """
    Resolves a mutation for creating a model instance through an adapter layer
    from the 'GraphQLFieldResolver' signature into the given ModelGraphQLMutation's
    MutationHandler's 'create' method signature. Also allows for pre- and post-save hooks
    defined in the ModelGraphQLMutation.
    """

    model_mutation: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> Model:
        input_data = kwargs[undine_settings.MUTATION_INPUT_TYPE_KEY]
        self.model_mutation.__pre_mutation__(None, info, input_data)

        with transaction.atomic(), handle_integrity_errors():
            instance = self.model_mutation.__mutation_handler__.create(input_data)

        self.model_mutation.__post_mutation__(instance, info, input_data)
        return instance


@dataclass(frozen=True, slots=True)
class UpdateResolver:
    """
    Resolves a mutation for updating a model instance through an adapter layer
    from the 'GraphQLFieldResolver' signature into the given ModelGraphQLMutation's
    MutationHandler's 'update' method signature. Also allows for pre- and post-save hooks
    defined in the ModelGraphQLMutation.
    """

    model_mutation: type[MutationType]

    @property
    def model(self) -> type[models.Model]:
        return self.model_mutation.__model__

    @property
    def lookup_field(self) -> str:
        return self.model_mutation.__lookup_field__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> Model:
        input_data = kwargs[undine_settings.MUTATION_INPUT_TYPE_KEY]
        value = input_data.get(self.lookup_field, Undefined)
        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key=self.lookup_field)

        instance = get_instance_or_raise(model=self.model, key=self.lookup_field, value=value)
        self.model_mutation.__pre_mutation__(instance, info, input_data)

        with transaction.atomic(), handle_integrity_errors():
            instance = self.model_mutation.__mutation_handler__.create(input_data)

        self.model_mutation.__post_mutation__(instance, info, input_data)
        return instance


@dataclass(frozen=True, slots=True)
class DeleteResolver:
    """
    Resolves a mutation for deleting a model instance through an adapter layer
    from the 'GraphQLFieldResolver' signature. Also allows for pre- and post-save
    hooks defined in the ModelGraphQLMutation.
    """

    model_mutation: type[MutationType]

    @property
    def model(self) -> type[models.Model]:
        return self.model_mutation.__model__

    @property
    def lookup_field(self) -> str:
        return self.model_mutation.__lookup_field__

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> dict[str, bool]:
        input_data = kwargs[undine_settings.MUTATION_INPUT_TYPE_KEY]
        value = input_data.get(self.lookup_field, Undefined)
        if value is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key=self.lookup_field)

        instance = get_instance_or_raise(model=self.model, key=self.lookup_field, value=value)
        self.model_mutation.__pre_mutation__(instance, info, input_data)

        with transaction.atomic(), handle_integrity_errors():
            instance.delete()

        self.model_mutation.__post_mutation__(None, info, input_data)
        return {"success": True}


@dataclass(frozen=True, slots=True)
class CustomResolver:
    """
    Resolves a mutation for custom mutations on a model instance through an adapter layer
    from the 'GraphQLFieldResolver' signature. Also allows for pre- and post-save
    hooks defined in the ModelGraphQLMutation.
    """

    model_mutation: type[MutationType]

    def __call__(self, root: Root, info: GQLInfo, **kwargs: Any) -> Any:
        input_data = kwargs[undine_settings.MUTATION_INPUT_TYPE_KEY]
        self.model_mutation.__pre_mutation__(None, info, input_data)

        with transaction.atomic(), handle_integrity_errors():
            return_value = self.model_mutation.__mutate__(root, info, input_data)

        self.model_mutation.__post_mutation__(return_value, info, input_data)
        return return_value
