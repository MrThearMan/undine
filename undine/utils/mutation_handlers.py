from __future__ import annotations

from collections import defaultdict
from functools import partial
from typing import TYPE_CHECKING, Any, Generic

from django.db.models import Model

from undine.dataclasses import PostSaveData
from undine.errors.exceptions import (
    GraphQLBulkMutationForwardRelationError,
    GraphQLBulkMutationGenericRelationsError,
    GraphQLBulkMutationManyRelatedError,
    GraphQLBulkMutationRelatedObjectNotFoundError,
    GraphQLBulkMutationReverseRelationError,
    GraphQLInvalidInputDataError,
    GraphQLModelNotFoundError,
)
from undine.parsers import parse_model_relation_info
from undine.parsers.parse_model_relation_info import RelationType
from undine.typing import JsonObject, RelatedManager, TModel
from undine.utils.model_utils import (
    generic_relations_for_generic_foreign_key,
    get_instance_or_raise,
    get_model_update_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine.parsers.parse_model_relation_info import RelatedFieldInfo


__all__ = [
    "BulkMutationHandler",
    "MutationHandler",
]


class MutationHandler(Generic[TModel]):
    """A class for creating or updating model instances while also handling related model instances."""

    def __init__(self, *, model: type[TModel]) -> None:
        self.model = model
        self.related_info = parse_model_relation_info(model=model)

    def get_update_or_create(self, data: dict[str, Any]) -> TModel | None:
        value = data.pop("pk", None)

        if value is None:
            return self.create(data)

        instance = get_instance_or_raise(model=self.model, key="pk", value=value)
        if not data:
            return instance

        return self.update(instance, data)

    def create(self, input_data: dict[str, Any]) -> TModel:
        """Create a new instance of the model, while also handling model relations."""
        post_save_data = self.pre_save(input_data)

        instance = self.model(**input_data)
        instance.full_clean()
        instance.save(force_insert=True)

        for handler in post_save_data.post_save_handlers:
            handler(instance)
        return instance

    def update(self, instance: TModel, input_data: dict[str, Any]) -> TModel:
        """Update an existing instance of the model, while also handling model relations."""
        post_save_data = self.pre_save(input_data)

        for attr, value in input_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save(update_fields=get_model_update_fields(self.model, *input_data))

        for handler in post_save_data.post_save_handlers:
            handler(instance)
        return instance

    def pre_save(self, input_data: dict[str, JsonObject | Model | list[Model] | None]) -> PostSaveData:
        """
        Make pre-save modifications to the given input data based on the model's relations.
        Forward 'one-to-one' and 'many-to-one' related entities will be fetched, updated, or created.
        Other related entities will be set to be handled after the main model is saved.
        """
        post_save_data = PostSaveData()

        for field_name in list(input_data):  # Copy keys so that we can .pop() in the loop
            # Only related fields need special handling.
            field_info = self.related_info.get(field_name, None)
            if field_info is None:
                continue

            # Remove the related field data from the input data for handling.
            # If there wasn't any data for that field, skip handling.
            related_data = input_data.pop(field_name)

            if isinstance(related_data, Model):
                input_data[field_name] = related_data

            elif field_info.relation_type.created_after:
                post_handler = self.get_post_save_handler(field_info, related_data)
                post_save_data.post_save_handlers.append(post_handler)

            elif field_info.relation_type.created_before:
                input_data[field_name] = self.handle_before_relation(field_info, related_data)

            elif field_info.relation_type.is_generic_foreign_key:
                input_data[field_name] = self.handle_generic_fk(field_info, related_data)

            else:  # pragma: no cover
                msg = f"Unhandled relation type: {field_info.relation_type}"
                raise TypeError(msg)

        return post_save_data

    def handle_before_relation(self, field_info: RelatedFieldInfo, data: Any) -> Any:
        if data is None and field_info.nullable:
            return data

        if isinstance(data, field_info.related_model_pk_type):
            return get_instance_or_raise(model=field_info.model, key="pk", value=data)

        if isinstance(data, dict):
            related_handler = MutationHandler(model=field_info.model)
            return related_handler.get_update_or_create(data)

        raise GraphQLInvalidInputDataError(field_name=field_info.field_name, data=data)

    def handle_generic_fk(self, field_info: RelatedFieldInfo, data: Any) -> Model:
        if not isinstance(data, dict):
            raise GraphQLInvalidInputDataError(field_name=field_info.field_name, data=data)

        typename = data.get("typename")
        if typename is None:
            msg = f"Missing 'typename' field in input data for field '{field_info.field_name}'."
            raise GraphQLInvalidInputDataError(msg)

        pk = data.get("pk")
        if pk is None:
            msg = f"Missing 'pk' field in input data for field '{field_info.field_name}'."
            raise GraphQLInvalidInputDataError(msg)

        generic_fk_field: GenericForeignKey = self.model._meta.get_field(field_info.field_name)
        related_model: type[Model] | None = next(
            (
                field.model
                for field in generic_relations_for_generic_foreign_key(generic_fk_field)
                if field.model.__name__ == typename
            ),
            None,
        )
        if related_model is None:
            msg = f"Field '{field_info.field_name}' does not have a relation to a model named '{typename}'."
            raise GraphQLInvalidInputDataError(msg)

        return get_instance_or_raise(model=related_model, key="pk", value=pk)

    def get_post_save_handler(self, field_info: RelatedFieldInfo, data: Any) -> Callable[[Model], Any]:
        """Get a post-save handler based on the relation type."""
        related_handler = MutationHandler(model=field_info.model)

        if field_info.relation_type == RelationType.REVERSE_ONE_TO_ONE:
            return partial(related_handler.post_handle_one_to_one, field_info=field_info, data=data)

        if field_info.relation_type == RelationType.REVERSE_ONE_TO_MANY:
            return partial(related_handler.post_handle_one_to_many, field_info=field_info, data=data)

        if field_info.relation_type == RelationType.GENERIC_ONE_TO_MANY:
            return partial(related_handler.post_handle_one_to_many, field_info=field_info, data=data)

        return partial(related_handler.post_handle_many_to_many, field_info=field_info, data=data)

    def post_handle_one_to_one(self, related_instance: Model, field_info: RelatedFieldInfo, data: Any) -> None:
        """Handle a reverse one-to-one relation after the related instance has been created."""
        # We need to remove the existing relation if we are replacing it
        existing_instance = getattr(related_instance, field_info.field_name, None)

        if data is None:
            if existing_instance is None:
                return

            if field_info.nullable:
                setattr(existing_instance, field_info.related_name, None)
                existing_instance.save(update_fields=[field_info.related_name])
                return

            existing_instance.delete()
            return

        if isinstance(data, dict):
            if existing_instance is not None and existing_instance.pk != data.get("pk"):
                if field_info.nullable:
                    setattr(existing_instance, field_info.related_name, None)
                    existing_instance.save(update_fields=[field_info.related_name])
                else:
                    existing_instance.delete()

            data[field_info.related_name] = related_instance
            self.get_update_or_create(data)
            return

        if isinstance(data, field_info.related_model_pk_type):
            new_instance = get_instance_or_raise(model=self.model, key="pk", value=data)

            if existing_instance is not None and existing_instance != new_instance:
                if field_info.nullable:
                    setattr(existing_instance, field_info.related_name, None)
                    existing_instance.save(update_fields=[field_info.related_name])
                else:
                    existing_instance.delete()

            setattr(new_instance, field_info.related_name, related_instance)
            new_instance.save(update_fields=get_model_update_fields(self.model, field_info.related_name))
            return

        raise GraphQLInvalidInputDataError(field_name=field_info.field_name, data=data)

    def post_handle_one_to_many(self, related_instance: Model, field_info: RelatedFieldInfo, data: Any) -> None:
        """Handle a reverse one-to-many relation after the related instance has been created."""
        manager: RelatedManager = getattr(related_instance, field_info.field_name)

        if not data:
            manager.all().delete()
            return

        if not isinstance(data, list):
            raise GraphQLInvalidInputDataError(field_name=field_info.field_name, data=data)

        pks: list[Any] = []
        for item in data:
            if isinstance(item, dict):
                item[field_info.related_name] = related_instance
                nested_instance = self.get_update_or_create(item)

            elif isinstance(item, field_info.related_model_pk_type):
                nested_instance = get_instance_or_raise(model=self.model, key="pk", value=item)

            else:
                raise GraphQLInvalidInputDataError(field_name=field_info.field_name, data=data)

            # Check that this entity belongs to this instance.
            existing_instance = getattr(nested_instance, field_info.related_name)
            if existing_instance != related_instance:
                setattr(nested_instance, field_info.related_name, related_instance)
                nested_instance.save(update_fields=get_model_update_fields(self.model, field_info.related_name))

            pks.append(nested_instance.pk)

        # Delete related objects that were not created or modified.
        manager.exclude(pk__in=pks).delete()

    def post_handle_many_to_many(self, related_instance: Model, field_info: RelatedFieldInfo, data: Any) -> None:
        """Handle a many-to-many relation after the related instance has been created."""
        manager: RelatedManager = getattr(related_instance, field_info.field_name)

        if not data:
            manager.clear()
            return

        if not isinstance(data, list):
            raise GraphQLInvalidInputDataError(field_name=field_info.field_name, data=data)

        instances: list[Model] = []
        for item in data:
            if isinstance(item, dict):
                nested_instance = self.get_update_or_create(item)

            elif isinstance(item, field_info.related_model_pk_type):
                nested_instance = get_instance_or_raise(model=self.model, key="pk", value=item)

            else:
                raise GraphQLInvalidInputDataError(field_name=field_info.field_name, data=data)

            instances.append(nested_instance)

        # Add related objects that were not previously linked to the main model.
        manager.set(instances)


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
        instances: list[Model],
        *,
        batch_size: int | None = None,
    ) -> list[TModel]:
        """
        Bulk update model instances while also handling model relations.
        Does not support reverse relations, many-to-many relations, generic relations,
        or creating new related objects.
        """
        self.pre_save(input_data)

        instances_by_pk: dict[int, Model] = {inst.pk: inst for inst in instances}

        for item in input_data:
            lookup_value = item.get("pk")
            instance = instances_by_pk.get(lookup_value)
            if instance is None:
                raise GraphQLModelNotFoundError(
                    key="pk",
                    value=lookup_value,
                    model=self.model,
                )

            for attr, value in item.items():
                setattr(instance, attr, value)
            instance.full_clean()

        # Update all fields except the lookup field.
        fields = list({field for data in input_data for field in data if field != "pk"})

        self.model._meta.default_manager.bulk_update(instances, fields, batch_size=batch_size)
        return instances

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

                if field_info.relation_type.is_many_to_many:
                    raise GraphQLBulkMutationManyRelatedError(name=field_name, model=field_info.model)

                if field_info.relation_type.is_reverse:
                    raise GraphQLBulkMutationReverseRelationError(name=field_name, model=field_info.model)

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
