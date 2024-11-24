from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Generic

from undine.errors.exceptions import (
    GraphQLBulkMutationForwardRelationError,
    GraphQLBulkMutationGenericRelationsError,
    GraphQLBulkMutationManyRelatedError,
    GraphQLBulkMutationRelatedObjectNotFoundError,
    GraphQLBulkMutationReverseRelationError,
    GraphQLModelNotFoundError,
)
from undine.parsers import parse_model_relation_info
from undine.typing import TModel

if TYPE_CHECKING:
    from django.db.models import Model


__all__ = [
    "BulkMutationHandler",
]


class BulkMutationHandler(Generic[TModel]):
    """A class for handling related objects and validations for bulk mutations."""

    def __init__(self, *, model: type[TModel]) -> None:
        self.model = model
        self.related_info = parse_model_relation_info(model=model)

    def create_many(
        self,
        input_data: list[dict[str, Any]],
        *,
        batch_size: int | None = None,
        ignore_conflicts: bool = False,
        update_conflicts: bool = False,
        update_fields: list[str] | None = None,
        unique_fields: list[str] | None = None,
    ) -> list[TModel]:
        """
        Bulk create model instances while also handling model relations.
        Does not support reverse relations, many-to-many relations, generic relations,
        or creating new related objects.
        """
        self.pre_save(input_data)

        instances: list[Model] = []
        for item in input_data:
            instance = self.model(**item)
            instance.full_clean()
            instances.append(instance)

        return self.model._meta.default_manager.bulk_create(
            instances,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )

    def update_many(
        self,
        input_data: list[dict[str, Any]],
        *,
        lookup_field: str,
        batch_size: int | None = None,
    ) -> list[TModel]:
        """
        Bulk update model instances while also handling model relations.
        Does not support reverse relations, many-to-many relations, generic relations,
        or creating new related objects.
        """
        self.pre_save(input_data)

        existing = self.model._meta.default_manager.filter(pk__in=[item[lookup_field] for item in input_data])
        instances: dict[int, Model] = {inst.pk: inst for inst in existing}

        for item in input_data:
            lookup_value = item.get(lookup_field)
            instance = instances.get(lookup_value)
            if instance is None:
                raise GraphQLModelNotFoundError(
                    key=lookup_field,
                    value=lookup_value,
                    model=self.model,
                )

            for attr, value in item.items():
                setattr(instance, attr, value)
            instance.full_clean()

        objs = list(instances.values())

        # Update all fields except the lookup field.
        fields = list({field for data in input_data for field in data if field != lookup_field})

        self.model._meta.default_manager.bulk_update(objs, fields, batch_size=batch_size)
        return objs

    def pre_save(self, input_data: list[dict[str, Any]]) -> None:
        """
        Make pre-save modifications to the given input data based on the model's relations.
        Only supports setting forward one-to-one and many-to-one relations from already existing
        related objects, which will be fetched in bulk and added to the corresponding fields in the input data.
        """
        related_object_data = self.get_relations_to_fetch(input_data)

        # Fetch related objects in bulk.
        instances: dict[type[Model], dict[int, Model]] = {}
        for model_cls, ids in related_object_data.items():
            instances[model_cls] = {instance.id: instance for instance in model_cls.objects.filter(id__in=ids)}

        self.set_relations(input_data, instances)

    def get_relations_to_fetch(self, input_data: list[dict[str, Any]]) -> dict[type[Model], set[int]]:
        """Determine which related objects from which models need to be fetched for the given input data."""
        related_objects_to_fetch: dict[type[Model], set[int]] = defaultdict(set)

        for item in input_data:
            for field_name, value in item.items():
                # Only related fields need special handling.
                field_info = self.related_info.get(field_name, None)
                if field_info is None:
                    continue

                if field_info.relation_type.created_before and isinstance(value, field_info.related_model_pk_type):
                    related_objects_to_fetch[field_info.model].add(value)
                    continue

                if field_info.relation_type.is_reverse:
                    raise GraphQLBulkMutationReverseRelationError(name=field_name, model=field_info.model)

                if field_info.relation_type.is_many_to_many:
                    raise GraphQLBulkMutationManyRelatedError(name=field_name, model=field_info.model)

                if field_info.relation_type.is_generic:
                    raise GraphQLBulkMutationGenericRelationsError(name=field_name, model=field_info.model)

                raise GraphQLBulkMutationForwardRelationError(name=field_name, model=field_info.model)

        return related_objects_to_fetch

    def set_relations(self, input_data: list[dict[str, Any]], instances: dict[type[Model], dict[int, Model]]) -> None:
        """Set fetched related objects in the input data."""
        for item in input_data:
            for field_name, value in item.items():
                field_info = self.related_info.get(field_name, None)
                if field_info is None:
                    continue

                if field_info.relation_type.created_before:
                    instance = instances.get(field_info.model, {}).get(value, None)
                    if instance is None:
                        raise GraphQLBulkMutationRelatedObjectNotFoundError(
                            name=field_name,
                            model=field_info.model,
                            value=value,
                        )

                    item[field_name] = instance
