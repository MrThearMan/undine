"""Contains a class for creating or updating model instances while also handling related model instances."""

from __future__ import annotations

import dataclasses
from functools import partial
from typing import TYPE_CHECKING, Any, Generic, Self

from django.db.models import Manager, Model
from graphql import Undefined

from undine.errors.exceptions import GraphQLBadInputDataError, GraphQLInvalidInputDataError
from undine.parsers import parse_model_relation_info
from undine.parsers.parse_model_relation_info import RelationType
from undine.settings import undine_settings
from undine.typing import (
    JsonType,
    ManyToManyManager,
    MutationInputType,
    OneToManyManager,
    PostSaveData,
    PostSaveHandler,
    TModel,
)
from undine.utils.model_utils import generic_relations_for_generic_foreign_key, get_instance_or_raise
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine import MutationType
    from undine.parsers.parse_model_relation_info import RelatedFieldInfo


__all__ = [
    "MutationHandler",
]


class MutationHandler(Generic[TModel]):
    """A class for creating or updating model instances while also handling related model instances."""

    def __init__(self, *, model: type[TModel]) -> None:
        self.model = model
        self.related_info = parse_model_relation_info(model)

    @property
    def manager(self) -> Manager:
        return self.model._default_manager  # type: ignore[return-value]

    def get_update_or_create(self, data: dict[str, Any]) -> TModel | None:
        key = "pk" if undine_settings.USE_PK_FIELD_NAME else self.model._meta.pk.name
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
        instance.save(update_fields=list(input_data.keys()))
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
            related_data = input_data.pop(field_name, Undefined)
            if related_data is Undefined:
                continue

            if isinstance(related_data, Model):
                input_data[field_name] = related_data

            elif field_info.relation_type.created_after:
                post_handler = self.get_post_save_handler(field_info, related_data)
                post_save_data.post_save_handlers.append(post_handler)

            elif field_info.relation_type.created_before:
                input_data[field_name] = self.handle_before_relation(field_info, related_data)

            elif field_info.relation_type.is_generic_foreign_key:
                input_data[field_name] = self.handle_generic_fk(field_info, related_data)

            else:
                msg = f"Unhandled relation type: {field_info.relation_type}"
                raise TypeError(msg)

        return post_save_data

    def handle_before_relation(self, field_info: RelatedFieldInfo, data: Any) -> Any:
        if (data is None and field_info.nullable) or isinstance(data, field_info.related_model_pk_type):
            return data

        if isinstance(data, dict):
            related_handler = MutationHandler(model=field_info.model)
            return related_handler.get_update_or_create(data)

        msg = f"Invalid input data for field '{field_info.field_name}': {data!r}"
        raise GraphQLInvalidInputDataError(msg)

    def handle_generic_fk(self, field_info: RelatedFieldInfo, data: Any) -> Model:
        if not isinstance(data, dict):
            msg = f"Invalid input data for field '{field_info.field_name}': {data!r}"
            raise GraphQLInvalidInputDataError(msg)

        typename = data.get("typename")
        if typename is None:
            msg = f"Missing 'typename' field in input data for field '{field_info.field_name}': {data!r}"
            raise GraphQLInvalidInputDataError(msg)

        pk = data.get("pk")
        if pk is None:
            msg = f"Missing 'pk' field in input data for field '{field_info.field_name}': {data!r}"
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
            msg = f"Field {field_info.field_name} does not have a relation to a model named '{typename}'."
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
        if data is None:
            if not field_info.nullable:
                msg = f"Field '{field_info.field_name}' cannot be null."
                raise GraphQLInvalidInputDataError(msg)

            instance: Model | None = getattr(related_instance, field_info.field_name, None)
            if instance is not None:
                instance.delete()
            return

        if isinstance(data, dict):
            data[field_info.related_name] = related_instance
            self.get_update_or_create(data)
            return

        if isinstance(data, field_info.related_model_pk_type):
            instance = get_instance_or_raise(model=self.model, key="pk", value=data)
            # TODO: Do we need to remove existing relation before this?
            setattr(instance, field_info.related_name, related_instance)
            instance.save(update_fields=[field_info.related_name])
            return

        msg = f"Invalid input data for field '{field_info.field_name}': {data!r}"
        raise GraphQLInvalidInputDataError(msg)

    def post_handle_one_to_many(self, related_instance: Model, field_info: RelatedFieldInfo, data: Any) -> None:
        """Handle a reverse one-to-many relation after the related instance has been created."""
        manager: OneToManyManager = getattr(related_instance, field_info.field_name)

        if data is None:
            # Remove relations from related models pointing to this model.
            # This only works for nullable relations.
            if not manager.field.null:
                msg = f"Related field '{field_info.related_name}' cannot be null."
                raise GraphQLInvalidInputDataError(msg)

            manager.clear()
            return

        if not isinstance(data, list):
            msg = f"Invalid input data for field '{field_info.field_name}': {data!r}"
            raise GraphQLInvalidInputDataError(msg)

        if not data:
            # Delete related objects pointing to this model.
            selector = {field_info.related_name: related_instance}
            self.manager.filter(**selector).delete()
            return

        pks: list[Any] = []
        for item in data:
            if isinstance(item, dict):
                item[field_info.related_name] = related_instance
                nested_instance = self.get_update_or_create(item)

            elif isinstance(item, field_info.related_model_pk_type):
                nested_instance = get_instance_or_raise(model=self.model, key="pk", value=item)

            else:
                msg = f"Invalid input data for field '{field_info.field_name}': {item!r}"
                raise GraphQLInvalidInputDataError(msg)

            pks.append(nested_instance.pk)

        # Delete related objects that were not created or modified.
        # TODO: Handle GenericRelation?
        if not field_info.relation_type.is_generic_relation:
            selector = {field_info.related_name: related_instance}
            self.manager.filter(**selector).exclude(pk__in=pks).delete()

    def post_handle_many_to_many(self, related_instance: Model, field_info: RelatedFieldInfo, data: Any) -> None:
        """Handle a many-to-many relation after the related instance has been created."""
        manager: ManyToManyManager = getattr(related_instance, field_info.field_name)

        if data is None:
            manager.clear()
            return

        if not isinstance(data, list):
            msg = f"Invalid input data for field '{field_info.field_name}': {data!r}"
            raise GraphQLInvalidInputDataError(msg)

        if not data:
            manager.clear()
            return

        instances: list[Model] = []
        for item in data:
            if isinstance(item, dict):
                nested_instance = self.get_update_or_create(item)

            elif isinstance(item, field_info.related_model_pk_type):
                nested_instance = get_instance_or_raise(model=self.model, key="pk", value=item)

            else:
                msg = f"Invalid input data for field '{field_info.field_name}': {item!r}"
                raise GraphQLInvalidInputDataError(msg)

            instances.append(nested_instance)

        # Add related objects that were not previously linked to the main model.
        manager.set(instances)


@dataclasses.dataclass
class MutationPreHandler:
    mutation_type: type[MutationType]
    input_data: dict[str, Any]

    input_only_data: dict[str, Any] = dataclasses.field(default_factory=dict, init=False)

    def __enter__(self) -> Self:
        self.input_only_data = extract_input_only_data(mutation_type=self.mutation_type, input_data=self.input_data)
        return self

    def __exit__(self, *args: object, **kwargs: Any) -> None:
        extend(target=self.input_data, to_merge=self.input_only_data)


def extract_input_only_data(mutation_type: type[MutationType], input_data: dict[str, Any]) -> JsonType:
    """
    Extracts all input-only field data from the given 'input_data'
    based on the undine.Inputs in the given MutationType.
    """
    from undine import MutationType

    input_only_data: JsonType = {}

    for field_name in list(input_data):  # Copy keys so that we can .pop() in the loop
        input_type = mutation_type.__input_map__.get(field_name)
        if input_type is None:
            raise GraphQLBadInputDataError(field_name=field_name)

        if input_type.input_only:
            input_only_data[field_name] = input_data.pop(field_name)
            continue

        value = input_data[field_name]

        if isinstance(value, dict) and is_subclass(input_type.ref, MutationType):
            data = extract_input_only_data(mutation_type=input_type.ref, input_data=value)
            if data:
                input_only_data[field_name] = data

        elif isinstance(value, list) and is_subclass(input_type.ref, MutationType):
            nested_data: list[JsonType] = []
            for item in value:
                data = extract_input_only_data(mutation_type=input_type.ref, input_data=item)
                if data:
                    nested_data.append(data)

            if nested_data:
                input_only_data[field_name] = nested_data

    return input_only_data


def extend(*, target: JsonType, to_merge: JsonType) -> JsonType:
    """
    Recursively extend 'other' JSON object into 'target' JSON object.
    If there is a conflict, the 'other' dictionary's value is used.
    """
    for key, value in to_merge.items():
        if key not in target:
            target[key] = value
        elif isinstance(target[key], dict) and isinstance(value, dict):
            extend(target=target[key], to_merge=value)
        elif isinstance(target[key], list) and isinstance(value, list):
            value.extend(value)
        else:
            target[key] = value

    return target
