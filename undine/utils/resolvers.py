from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, TypeGuard

from graphql import GraphQLResolveInfo

from undine.settings import undine_settings

from .reflection import get_signature

if TYPE_CHECKING:
    from types import FunctionType

    from django.db import models
    from graphql import GraphQLFieldResolver

    from undine.typing import RelatedManager

__all__ = [
    "FieldResolver",
    "FieldResolverWithInfo",
    "FieldResolverWithRoot",
    "FieldResolverWithRootAndInfo",
    "ModelFieldResolver",
    "ModelManyRelatedResolver",
    "MutationResolver",
    "function_field_resolver",
    "model_field_resolver",
]


def model_field_resolver(*, name: str, many: bool = False) -> GraphQLFieldResolver:
    """Find a model attribute resolver, either for a regular field or a related field."""
    return ModelManyRelatedResolver(name=name) if many else ModelFieldResolver(name=name)


def function_field_resolver(func: FunctionType, *, depth: int = 0) -> GraphQLFieldResolver:
    """
    Find the appropriate GraphQL field resolver for a function based on its signature.
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

        elif is_graphql_resolver_info(param.annotation):
            info_param = param.name
            break

    if root_param and info_param:
        return FieldResolverWithRootAndInfo(func=func, root_param=root_param, info_param=info_param)
    if root_param:
        return FieldResolverWithRoot(func=func, root_param=root_param)
    if info_param:
        return FieldResolverWithInfo(func=func, info_param=info_param)

    return FieldResolver(func=func)


@dataclass(frozen=True, slots=True)
class ModelFieldResolver:
    name: str

    def __call__(self, model: models.Model, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        return getattr(model, self.name, None)


@dataclass(frozen=True, slots=True)
class ModelManyRelatedResolver:
    name: str

    def __call__(self, model: models.Model, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        related_manager: RelatedManager = getattr(model, self.name)
        return related_manager.get_queryset()


@dataclass(frozen=True, slots=True)
class FieldResolver:
    func: FunctionType | Callable[..., Any]
    other_params: list[str] = field(default_factory=list)

    def __call__(self, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        return self.func(**kwargs)


@dataclass(frozen=True, slots=True)
class FieldResolverWithRoot:
    func: FunctionType | Callable[..., Any]
    root_param: str
    other_params: list[str] = field(default_factory=list)

    def __call__(self, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        kwargs[self.root_param] = root
        return self.func(**kwargs)


@dataclass(frozen=True, slots=True)
class FieldResolverWithInfo:
    func: FunctionType | Callable[..., Any]
    info_param: str
    other_params: list[str] = field(default_factory=list)

    def __call__(self, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        kwargs[self.info_param] = info
        return self.func(**kwargs)


@dataclass(frozen=True, slots=True)
class FieldResolverWithRootAndInfo:
    func: FunctionType | Callable[..., Any]
    root_param: str
    info_param: str
    other_params: list[str] = field(default_factory=list)

    def __call__(self, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        kwargs[self.root_param] = root
        kwargs[self.info_param] = info
        return self.func(**kwargs)


@dataclass(frozen=True)
class MutationResolver:
    func: FunctionType | Callable[..., Any]

    def __call__(self, root: Any, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        input_data = kwargs[undine_settings.MUTATION_INPUT_TYPE_KEY]
        return self.func(root, info, input_data)


def is_graphql_resolver_info(value: Any) -> TypeGuard[GraphQLResolveInfo]:
    """Check is the given value is the GraphQLResolveInfo."""
    return isinstance(value, type) and issubclass(value, GraphQLResolveInfo)
