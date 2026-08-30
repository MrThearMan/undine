"""
Contains different types of resolvers for GraphQL operations.
Resolvers must be callables with the following signature:

(root: Root, info: GQLInfo, **kwargs: Any) -> Any
"""

from __future__ import annotations

from .filter import FilterFunctionResolver, FilterModelFieldResolver, FilterQExpressionResolver
from .mutation import (
    BulkCreateResolver,
    BulkDeleteResolver,
    BulkUpdateResolver,
    CreateResolver,
    DeleteResolver,
    UpdateResolver,
)
from .query import (
    ConnectionResolver,
    EntrypointFunctionResolver,
    FieldFunctionResolver,
    GlobalIDResolver,
    InterfaceTypeConnectionResolver,
    InterfaceTypeResolver,
    ModelAttributeResolver,
    ModelGenericForeignKeyResolver,
    ModelManyRelatedFieldResolver,
    ModelSingleRelatedFieldResolver,
    NamedTupleFieldResolver,
    NestedConnectionResolver,
    NestedQueryTypeManyResolver,
    NestedQueryTypeSingleResolver,
    NodeResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
    TypedDictFieldResolver,
    UnionTypeConnectionResolver,
    UnionTypeResolver,
)
from .subscription import FunctionSubscriptionResolver, SubscriptionValueResolver

__all__ = [
    "BulkCreateResolver",
    "BulkDeleteResolver",
    "BulkUpdateResolver",
    "ConnectionResolver",
    "CreateResolver",
    "DeleteResolver",
    "EntrypointFunctionResolver",
    "FieldFunctionResolver",
    "FilterFunctionResolver",
    "FilterModelFieldResolver",
    "FilterQExpressionResolver",
    "FunctionSubscriptionResolver",
    "GlobalIDResolver",
    "InterfaceTypeConnectionResolver",
    "InterfaceTypeResolver",
    "ModelAttributeResolver",
    "ModelGenericForeignKeyResolver",
    "ModelManyRelatedFieldResolver",
    "ModelSingleRelatedFieldResolver",
    "NamedTupleFieldResolver",
    "NestedConnectionResolver",
    "NestedQueryTypeManyResolver",
    "NestedQueryTypeSingleResolver",
    "NodeResolver",
    "QueryTypeManyResolver",
    "QueryTypeSingleResolver",
    "SubscriptionValueResolver",
    "TypedDictFieldResolver",
    "UnionTypeConnectionResolver",
    "UnionTypeResolver",
    "UpdateResolver",
]
