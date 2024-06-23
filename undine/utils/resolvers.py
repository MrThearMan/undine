from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.db import models
    from graphql import GraphQLFieldResolver, GraphQLResolveInfo

__all__ = [
    "model_attr_resolver",
    "model_to_many_resolver",
]


def model_attr_resolver(*, name: str) -> GraphQLFieldResolver:
    def resolver(model: models.Model, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        return getattr(model, name, None)

    return resolver


def model_to_many_resolver(*, name: str) -> GraphQLFieldResolver:
    def resolver(model: models.Model, info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        return getattr(model, name).get_queryset()

    return resolver
