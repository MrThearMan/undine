from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from django.db.models import ForeignKey, ManyToOneRel, Model, QuerySet

from undine.errors import OptimizerError
from undine.settings import undine_settings
from undine.utils.logging import undine_logger
from undine.utils.reflection import swappable_by_subclassing

from .ast import GraphQLASTWalker
from .optimizer import QueryOptimizer

if TYPE_CHECKING:
    from django.db import models
    from graphql import FieldNode, GraphQLOutputType, GraphQLResolveInfo

    from undine import Field
    from undine.typing import ToManyField, ToOneField


__all__ = [
    "OptimizationCompiler",
]


@swappable_by_subclassing
class OptimizationCompiler(GraphQLASTWalker):
    """Class for compiling SQL optimizations based on the given query."""

    def __init__(self, info: GraphQLResolveInfo, max_complexity: int | None = None) -> None:
        """
        Initialize the optimization compiler with the query info.

        :param info: The GraphQLResolveInfo containing the query AST.
        :param max_complexity: How many 'select_related' and 'prefetch_related' table joins are allowed.
                               Used to protect from malicious queries.
        """
        self.max_complexity = max_complexity or undine_settings.OPTIMIZER_MAX_COMPLEXITY
        self.optimizer: QueryOptimizer = None  # type: ignore[assignment]
        self.to_attr: str | None = None
        super().__init__(info)

    def compile(self, queryset: QuerySet) -> QueryOptimizer | None:
        """
        Compile optimizations for the given queryset.

        :return: QueryOptimizer instance that can perform any needed optimization,
                 or None if queryset is already optimized.
        """
        # Setup initial state.
        self.model = queryset.model
        self.optimizer = QueryOptimizer(model=queryset.model, info=self.info)
        # Walk the query AST to compile the optimizations.
        self.run()
        return self.optimizer

    def increase_complexity(self) -> None:
        super().increase_complexity()
        if self.complexity > self.max_complexity:
            msg = f"Query complexity exceeds the maximum allowed of {self.max_complexity}"
            raise OptimizerError(msg)

    def handle_normal_field(self, field_type: GraphQLOutputType, field_node: FieldNode, field: models.Field) -> None:
        self.optimizer.only_fields.append(field.get_attname())

    def handle_to_one_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToOneField,
        related_model: type[Model] | None,
    ) -> None:
        from django.contrib.contenttypes.fields import GenericForeignKey

        name = self.get_related_field_name(related_field)
        optimizer = QueryOptimizer(model=related_model, info=self.info, name=name, parent=self.optimizer)

        if isinstance(related_field, GenericForeignKey):
            optimizer = self.optimizer.prefetch_related.setdefault(name, optimizer)
        else:
            optimizer = self.optimizer.select_related.setdefault(name, optimizer)

        if isinstance(related_field, ForeignKey):
            self.optimizer.related_fields.append(related_field.attname)

        if isinstance(related_field, GenericForeignKey):
            self.optimizer.related_fields.append(related_field.ct_field)
            self.optimizer.related_fields.append(related_field.fk_field)

        with self.use_optimizer(optimizer):
            super().handle_to_one_field(parent_type, field_node, related_field, related_model)

    def handle_to_many_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[Model] | None,
    ) -> None:
        from django.contrib.contenttypes.fields import GenericRelation

        name = self.get_related_field_name(related_field)
        alias = getattr(field_node.alias, "value", None)
        key = self.to_attr if self.to_attr is not None else alias if alias is not None else name
        self.to_attr = None

        optimizer = QueryOptimizer(model=related_model, info=self.info, name=name, parent=self.optimizer)
        optimizer = self.optimizer.prefetch_related.setdefault(key, optimizer)

        if isinstance(related_field, ManyToOneRel):
            optimizer.related_fields.append(related_field.field.attname)

        if isinstance(related_field, GenericRelation):
            optimizer.related_fields.append(related_field.object_id_field_name)
            optimizer.related_fields.append(related_field.content_type_field_name)

        with self.use_optimizer(optimizer):
            super().handle_to_many_field(parent_type, field_node, related_field, related_model)

    def handle_custom_field(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        field = field_type.fields.get(field_node.name.value)
        if field is not None:
            undine_field: Field | None = field.extensions.get(undine_settings.FIELD_EXTENSIONS_KEY)
            if undine_field is not None:
                return undine_field.optimizer_hook(self.optimizer)

        msg = (
            f"Field '{field_node.name.value}' not found from object type '{field_type}'. "
            f"Cannot optimize custom field."
        )
        undine_logger.warning(msg)
        return None

    @contextlib.contextmanager
    def use_optimizer(self, optimizer: QueryOptimizer) -> None:
        orig_optimizer = self.optimizer
        try:
            self.optimizer = optimizer
            yield
        finally:
            self.optimizer = orig_optimizer
