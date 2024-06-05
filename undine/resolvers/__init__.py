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
    CustomResolver,
    DeleteResolver,
    UpdateResolver,
)
from .query import (
    ConnectionResolver,
    EntrypointFunctionResolver,
    FieldFunctionResolver,
    GlobalIDResolver,
    ModelAttributeResolver,
    ModelGenericForeignKeyResolver,
    ModelManyRelatedFieldResolver,
    ModelSingleRelatedFieldResolver,
    NestedConnectionResolver,
    NestedQueryTypeManyResolver,
    NestedQueryTypeSingleResolver,
    NodeResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
)

__all__ = [
    "BulkCreateResolver",
    "BulkDeleteResolver",
    "BulkUpdateResolver",
    "ConnectionResolver",
    "CreateResolver",
    "CustomResolver",
    "DeleteResolver",
    "EntrypointFunctionResolver",
    "EntrypointFunctionResolver",
    "FieldFunctionResolver",
    "FilterFunctionResolver",
    "FilterModelFieldResolver",
    "FilterQExpressionResolver",
    "GlobalIDResolver",
    "ModelAttributeResolver",
    "ModelGenericForeignKeyResolver",
    "ModelManyRelatedFieldResolver",
    "ModelSingleRelatedFieldResolver",
    "NestedConnectionResolver",
    "NestedQueryTypeManyResolver",
    "NestedQueryTypeSingleResolver",
    "NodeResolver",
    "QueryTypeManyResolver",
    "QueryTypeSingleResolver",
    "UpdateResolver",
]
