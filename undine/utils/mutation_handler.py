"""Contains a class for creating or updating model instances while also handling related model instances."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, Generic, Iterable

from django.db.models import Manager, Model

from undine.errors.exceptions import GraphQLInvalidInputDataError
from undine.parsers import parse_model_relation_info
from undine.parsers.parse_model_relation_info import RelationType
from undine.typing import ManyToManyManager, MutationInputType, OneToManyManager, PostSaveData, PostSaveHandler, TModel
from undine.utils.model_utils import (
    generic_relations_for_generic_foreign_key,
    get_instance_or_raise,
    get_lookup_field_name,
)

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine.parsers.parse_model_relation_info import RelatedFieldInfo


__all__ = [
    "MutationHandler",
]


class MutationHandler(Generic[TModel]):
    """A class for creating or updating model instances while also handling related model instances."""

    def __init__(self, *, model: type[TModel]) -> None:
        self.model = model
        self.related_info = parse_model_relation_info(model=model)

    @property
    def manager(self) -> Manager:
        return self.model._default_manager  # type: ignore[return-value]

    def get_update_or_create(self, data: dict[str, Any]) -> TModel | None:
        key = get_lookup_field_name(self.model)
        value = data.pop(key, None)

        if value is None:
            return self.create(data)

        instance = get_instance_or_raise(model=self.model, key=key, value=value)
        if not data:
            return instance

        return self.update(instance, data)

    def create(self, input_data: dict[str, Any]) -> TModel:
        """Create a new instance of the model, while also handling model relations."""
        post_save_data = self.pre_save(input_data)

        instance = self.manager.create(**input_data)

        for handler in post_save_data.post_save_handlers:
            handler(instance)
        return instance

    def update(self, instance: TModel, input_data: dict[str, Any]) -> TModel:
        """Update an existing instance of the model, while also handling model relations."""
        post_save_data = self.pre_save(input_data)

        for attr, value in input_data.items():
            setattr(instance, attr, value)
        instance.save(update_fields=self.get_update_fields(*input_data))

        for handler in post_save_data.post_save_handlers:
            handler(instance)
        return instance

    def pre_save(self, input_data: dict[str, MutationInputType]) -> PostSaveData:
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

    def get_post_save_handler(self, field_info: RelatedFieldInfo, data: Any) -> PostSaveHandler:
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
            if existing_instance is not None and existing_instance.pk != data.get(get_lookup_field_name(self.model)):
                if field_info.nullable:
                    setattr(existing_instance, field_info.related_name, None)
                    existing_instance.save(update_fields=[field_info.related_name])
                else:
                    existing_instance.delete()

            data[field_info.related_name] = related_instance
            self.get_update_or_create(data)
            return

        if isinstance(data, field_info.related_model_pk_type):
            instance = get_instance_or_raise(model=self.model, key="pk", value=data)
            if existing_instance is not None and existing_instance != instance:
                if field_info.nullable:
                    setattr(existing_instance, field_info.related_name, None)
                    existing_instance.save(update_fields=[field_info.related_name])
                else:
                    existing_instance.delete()

            setattr(instance, field_info.related_name, related_instance)
            instance.save(update_fields=self.get_update_fields(field_info.related_name))
            return

        raise GraphQLInvalidInputDataError(field_name=field_info.field_name, data=data)

    def post_handle_one_to_many(self, related_instance: Model, field_info: RelatedFieldInfo, data: Any) -> None:
        """Handle a reverse one-to-many relation after the related instance has been created."""
        # This can also be a `GenericRelatedObjectManager`, but typing that requires
        # the content type app to be loaded to create the type, so this is fine.
        manager: OneToManyManager = getattr(related_instance, field_info.field_name)

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
                nested_instance.save(update_fields=self.get_update_fields(field_info.related_name))

            pks.append(nested_instance.pk)

        # Delete related objects that were not created or modified.
        manager.exclude(pk__in=pks).delete()

    def post_handle_many_to_many(self, related_instance: Model, field_info: RelatedFieldInfo, data: Any) -> None:
        """Handle a many-to-many relation after the related instance has been created."""
        manager: ManyToManyManager = getattr(related_instance, field_info.field_name)

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

    def get_update_fields(self, *fields: str) -> Iterable[str] | None:
        # 'GenericForeignKey' fields or 'pk' properties cannot be in the 'update_fields' set.
        # If they are, we cannot optimize the update to only the fields actually updated.
        if set(fields).issubset(self.model._meta._non_pk_concrete_field_names):
            return fields
        return None
