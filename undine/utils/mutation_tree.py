from __future__ import annotations

import dataclasses
from collections import defaultdict
from functools import partial
from typing import TYPE_CHECKING, Any, Self

from django.db import transaction  # noqa: ICN003
from django.db.models import Q

from undine.exceptions import (
    GraphQLInvalidInputDataError,
    GraphQLMutationTreeModelMismatchError,
    GraphQLRelationMultipleInstancesError,
    GraphQLRelationNotNullableError,
)
from undine.parsers import parse_model_relation_info
from undine.settings import undine_settings
from undine.typing import RelatedAction, RelationType
from undine.utils.model_utils import (
    generic_relations_for_generic_foreign_key,
    get_bulk_create_kwargs,
    get_default_manager,
    get_instance_or_raise,
    get_instances_or_raise,
    set_forward_ids,
    use_delete_signals,
    use_m2m_add_signals,
    use_m2m_remove_signals,
    use_save_signals,
)
from undine.utils.text import to_camel_case

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.db.models import Model
    from django.db.models.fields.related_descriptors import ForeignKeyDeferredAttribute, ManyToManyDescriptor

    from undine.dataclasses import RelInfo
    from undine.typing import TModel

__all__ = [
    "bulk_mutate",
    "mutate",
]


@transaction.atomic
def mutate(
    *,
    model: type[TModel],
    data: dict[str, Any],
    related_action: RelatedAction = RelatedAction.null,
) -> TModel:
    """Mutate objects using the given data and model."""
    start_node = MutationNode(model=model, related_action=related_action)
    start_node.handle_one(data)
    return start_node.mutate()[0]  # type: ignore[return-value]


@transaction.atomic
def bulk_mutate(
    *,
    model: type[TModel],
    data: list[dict[str, Any]],
    related_action: RelatedAction = RelatedAction.null,
) -> list[TModel]:
    """Bulk mutate objects using the given data and model."""
    start_node = MutationNode(model=model, related_action=related_action)
    start_node.handle_many(data)
    return start_node.mutate()  # type: ignore[return-value]


@dataclasses.dataclass(slots=True, kw_only=True)
class MutationNode:
    """
    A node in a tree of mutations.
    Contains instances of a model that should be updated or created.
    May link to other `MutationNodes` to create a tree of mutations
    that can be mutated efficiently.
    """

    model: type[Model]
    """The model that this node is for."""

    related_action: RelatedAction = RelatedAction.null
    """What happens to related objects that are not included in the input?"""

    mutation_func: Callable[[], list[Model]] = dataclasses.field(init=False)
    """The function that should be run to mutate the instances."""

    instances: list[Model] = dataclasses.field(default_factory=list)
    """The instances that should be updated or created."""

    field_names: set[str] = dataclasses.field(default_factory=set)
    """Fields that are present in the input data."""

    before: dict[str, MutationNode] = dataclasses.field(default_factory=dict)
    """Mutations that should be run before this one."""

    after: dict[str, MutationNode] = dataclasses.field(default_factory=dict)
    """Mutations that should be run after this one."""

    def __post_init__(self) -> None:
        self.mutation_func = self.mutate_bulk

    # Mutation handling

    def mutate(self, *, previous_node: MutationNode | None = None) -> list[Model]:
        """Run the mutations starting from this node."""
        for before_node in self.before.values():
            if before_node != previous_node:
                before_node.mutate(previous_node=self)

        instances = self.mutation_func()

        for after_node in self.after.values():
            if after_node != previous_node:
                after_node.mutate(previous_node=self)

        return instances

    def mutate_bulk(self) -> list[Model]:
        """Mutate model instances using the `queryset.bulk_create` method."""
        kwargs = get_bulk_create_kwargs(self.model, *self.field_names)

        instances: list[Model] = []
        for instance in self.instances:
            # Only save new instances if no fields to update
            if kwargs.update_fields or instance.pk is None:
                set_forward_ids(instance)
                if undine_settings.MUTATION_FULL_CLEAN:
                    instance.full_clean()
                instances.append(instance)

        with use_save_signals(self.model, instances, kwargs.update_fields):
            get_default_manager(self.model).bulk_create(objs=instances, **kwargs)

        return self.instances

    def mutate_delete(self) -> list[Model]:
        """Delete model instance s using the `queryset.delete` method."""
        pks = [instance.pk for instance in self.instances]
        with use_delete_signals(self.model, self.instances):
            get_default_manager(self.model).filter(pk__in=pks).delete()
        return []

    def mutate_through(self, *, source_name: str, target_name: str, reverse: bool, symmetrical: bool) -> list[Model]:
        through_map: defaultdict[Model, dict[Model, Model]] = defaultdict(dict)

        # Add new instances
        for through_instance in self.instances:
            set_forward_ids(through_instance)
            if undine_settings.MUTATION_FULL_CLEAN:
                through_instance.full_clean()

            source = getattr(through_instance, source_name)
            target = getattr(through_instance, target_name)
            through_map[source][target] = through_instance

        # Order matters here, since '_upsert_through()' will backfill symmetrical instances to the 'through_map'
        # but '_remove_through()' should not remove any rows in the backwards direction that are
        # not updated during this mutation.
        self._remove_through(
            through_map,
            source_name=source_name,
            target_name=target_name,
            reverse=reverse,
            symmetrical=symmetrical,
        )
        self._upsert_through(
            through_map,
            source_name=source_name,
            target_name=target_name,
            reverse=reverse,
            symmetrical=symmetrical,
        )
        return self.instances

    # Data handling

    def handle_one(self, data: dict[str, Any]) -> Model:
        """Handle data for a single object."""
        pk = data.get("pk")
        # We need to fetch the existing instance so that non-updated fields are present during bulk-create.
        instance = self.model() if pk is None else get_instance_or_raise(model=self.model, pk=pk)

        self.instances.append(instance)
        self.handle_data(data, instance)
        return instance

    def handle_many(self, data: list[dict[str, Any]]) -> list[Model]:
        """Handle data for many objects."""
        instances: list[Model] = []

        instance_map: dict[Any, Model] = {}
        pks = [item["pk"] for item in data if "pk" in item]
        if pks:
            # We need to fetch existing instances so that non-updated fields are present during bulk-create.
            instance_map = {inst.pk: inst for inst in get_instances_or_raise(model=self.model, pks=pks)}

        for item in data:
            pk = item.get("pk")
            instance = instance_map.get(pk) or self.model()

            self.instances.append(instance)
            self.handle_data(item, instance)
            instances.append(instance)

        return instances

    def handle_data(self, data: dict[str, Any], instance: Model) -> Self:
        relation_info = parse_model_relation_info(model=self.model)

        for field_name, field_data in data.items():
            rel_info = relation_info.get(field_name)
            if rel_info is None:
                self.field_names.add(field_name)
                setattr(instance, field_name, field_data)
                continue

            node = MutationNode(model=rel_info.related_model, related_action=self.related_action)  # type: ignore[arg-type]
            self.handle_relation(field_data, rel_info, instance, node)

        return self

    # Relation handing

    def handle_relation(self, data: Any, rel_info: RelInfo, instance: Model, node: MutationNode) -> None:
        match rel_info.relation_type:
            case RelationType.FORWARD_ONE_TO_ONE:
                self._handle_forward_o2o(data, rel_info, instance, node)

            case RelationType.FORWARD_MANY_TO_ONE:
                self._handle_m2o(data, rel_info, instance, node)

            case RelationType.FORWARD_MANY_TO_MANY:
                self._handle_m2m(data, rel_info, instance, node)

            case RelationType.REVERSE_ONE_TO_ONE:
                self._handle_reverse_o2o(data, rel_info, instance, node)

            case RelationType.REVERSE_ONE_TO_MANY:
                self._handle_o2m(data, rel_info, instance, node)

            case RelationType.REVERSE_MANY_TO_MANY:
                self._handle_m2m(data, rel_info, instance, node)

            case RelationType.GENERIC_ONE_TO_MANY:
                self._handle_o2m(data, rel_info, instance, node)

            case RelationType.GENERIC_MANY_TO_ONE:
                self._handle_generic_fk(data, rel_info, instance, node)

            case _:  # pragma: no cover
                msg = f"Unhandled relation type: {rel_info.relation_type}"
                raise NotImplementedError(msg)

    def _handle_forward_o2o(self, data: Any, rel_info: RelInfo, instance: Model, node: MutationNode) -> None:
        """Handle forward one-to-one relations for the given instance."""
        match data:
            case dict():
                rel = node.handle_one(data=data)

                setattr(instance, rel_info.field_name, rel)
                self.field_names.add(rel_info.field_name)  # type: ignore[arg-type]

            case rel_info.related_model_pk_type():
                rel = get_instance_or_raise(model=node.model, pk=data)

                node.instances.append(rel)

                setattr(instance, rel_info.field_name, rel)
                self.field_names.add(rel_info.field_name)  # type: ignore[arg-type]

            case rel_info.related_model():
                node.instances.append(data)

                setattr(instance, rel_info.field_name, data)
                self.field_names.add(rel_info.field_name)  # type: ignore[arg-type]

            case None:
                if not rel_info.related_nullable:
                    raise GraphQLRelationNotNullableError(field_name=rel_info.field_name, model=self.model)

                setattr(instance, rel_info.field_name, None)
                self.field_names.add(rel_info.field_name)  # type: ignore[arg-type]

            case _:
                raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

        self.put_before(node, field_name=rel_info.field_name, related_name=rel_info.related_name)  # type: ignore[arg-type]

    _handle_m2o = _handle_forward_o2o
    """Handle many-to-one relations for the given instance."""

    def _handle_reverse_o2o(self, data: Any, rel_info: RelInfo, instance: Model, node: MutationNode) -> None:
        """Handle reverse one-to-one relations for the given instance."""
        existing_instance: Model | None = getattr(instance, rel_info.field_name, None)

        match data:
            case dict():
                rel = node.handle_one(data=data)

                setattr(rel, rel_info.related_name, instance)  # type: ignore[arg-type]
                node.field_names.add(rel_info.related_name)  # type: ignore[arg-type]

            case rel_info.related_model_pk_type():
                rel = get_instance_or_raise(model=node.model, pk=data)

                node.instances.append(rel)

                setattr(rel, rel_info.related_name, instance)  # type: ignore[arg-type]
                node.field_names.add(rel_info.related_name)  # type: ignore[arg-type]

            case rel_info.related_model():
                node.instances.append(data)

                setattr(data, rel_info.related_name, instance)  # type: ignore[arg-type]
                node.field_names.add(rel_info.related_name)  # type: ignore[arg-type]

            case None:
                # If creating, no related instance is created.
                # If updating, there might be a related instance.
                # What happens to it depends on the "related action" set by the mutation type.
                pass

            case _:
                raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

        self.put_after(node, field_name=rel_info.field_name, related_name=rel_info.related_name)  # type: ignore[arg-type]

        if existing_instance is not None:
            updated_instances: set[Model] = {instance for instance in node.instances if instance.pk is not None}
            non_updated_instances: set[Model] = {existing_instance} - updated_instances

            if non_updated_instances:
                match self.related_action:
                    case RelatedAction.null:
                        self._disconnect_instances(non_updated_instances, rel_info, node)
                    case RelatedAction.delete:
                        self._remove_instances(non_updated_instances, rel_info, node)
                    case RelatedAction.ignore:
                        raise GraphQLRelationMultipleInstancesError(
                            field_name=rel_info.related_name,
                            model=rel_info.related_model,
                        )

    def _handle_o2m(self, data: list[Any], rel_info: RelInfo, instance: Model, node: MutationNode) -> None:  # noqa: C901,PLR0912
        """Handle one-to-many relations for the given instance."""
        existing_instances: set[Model] = set()
        if instance.pk is not None:
            existing_instances = set(getattr(instance, rel_info.field_name).all())

        match data:
            case [dict(), *_]:
                instances = node.handle_many(data=data)

                for rel in instances:
                    setattr(rel, rel_info.related_name, instance)  # type: ignore[arg-type]

                node.field_names.add(rel_info.related_name)  # type: ignore[arg-type]

            case [rel_info.related_model_pk_type(), *_]:
                for rel in get_instances_or_raise(model=node.model, pks=data):
                    node.instances.append(rel)
                    setattr(rel, rel_info.related_name, instance)  # type: ignore[arg-type]

                node.field_names.add(rel_info.related_name)  # type: ignore[arg-type]

            case [rel_info.related_model(), *_]:
                for rel in data:
                    node.instances.append(rel)
                    setattr(rel, rel_info.related_name, instance)  # type: ignore[arg-type]

                node.field_names.add(rel_info.related_name)  # type: ignore[arg-type]

            case [None, *_] | [] | None:
                # If creating, do not add related instances.
                # If updating, all instances will be "non-updated" instances.
                # What happens to them depends on the "related action" set by the mutation type.
                pass

            case _:
                raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

        self.put_after(node, field_name=rel_info.field_name, related_name=rel_info.related_name)  # type: ignore[arg-type]

        if existing_instances:
            updated_instances: set[Model] = {instance for instance in node.instances if instance.pk is not None}
            non_updated_instances: set[Model] = existing_instances - updated_instances

            if non_updated_instances:
                match self.related_action:
                    case RelatedAction.null:
                        self._disconnect_instances(non_updated_instances, rel_info, node)
                    case RelatedAction.delete:
                        self._remove_instances(non_updated_instances, rel_info, node)
                    case RelatedAction.ignore:
                        pass

    def _handle_m2m(self, data: list[Any], rel_info: RelInfo, instance: Model, node: MutationNode) -> None:
        """Handle many-to-many relations for the given instance."""
        match data:
            case [dict(), *_]:
                node.handle_many(data=data)

            case [rel_info.related_model_pk_type(), *_]:
                for rel in get_instances_or_raise(model=node.model, pks=data):
                    node.instances.append(rel)

            case [rel_info.related_model(), *_]:
                for rel in data:
                    node.instances.append(rel)

            case [None, *_] | [] | None:
                node.instances = []

            case _:
                raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

        node._handle_through(instance, rel_info)

        self.put_after(node, field_name=rel_info.field_name, related_name=rel_info.related_name)  # type: ignore[arg-type]

    def _handle_through(self, source: Model, rel_info: RelInfo) -> None:
        """Handle the through model instances for a many-to-many relation."""
        m2m: ManyToManyDescriptor = getattr(type(source), rel_info.field_name)
        reverse = rel_info.relation_type.is_reverse
        source_name = m2m.field.m2m_reverse_field_name() if reverse else m2m.field.m2m_field_name()
        target_name = m2m.field.m2m_field_name() if reverse else m2m.field.m2m_reverse_field_name()
        symmetrical = m2m.rel.symmetrical

        node = MutationNode(model=m2m.through, related_action=self.related_action)  # type: ignore[arg-type]
        node.mutation_func = partial(
            node.mutate_through,
            source_name=source_name,
            target_name=target_name,
            reverse=reverse,
            symmetrical=symmetrical,
        )

        for target in self.instances:
            through_instance = node.model()
            setattr(through_instance, source_name, source)
            setattr(through_instance, target_name, target)

            node.instances.append(through_instance)
            node.field_names.add(source_name)
            node.field_names.add(target_name)

        attr: ForeignKeyDeferredAttribute = getattr(m2m.through, source_name)
        hidden_field_name = attr.field.remote_field.get_accessor_name()

        self.put_after(node, field_name=hidden_field_name, related_name=source_name)  # type: ignore[arg-type]

    def _handle_generic_fk(self, data: Any, rel_info: RelInfo, instance: Model, node: MutationNode) -> None:
        """Handle generic foreign key relations for the given instance."""
        if not isinstance(data, dict):
            raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

        key: str | None = next(iter(data), None)
        if key is None:
            raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

        model_data: dict[str, Any] = data[key]

        field: GenericForeignKey = rel_info.model._meta.get_field(rel_info.field_name)  # type: ignore[assignment]
        relations = generic_relations_for_generic_foreign_key(field)
        related_model_map = {to_camel_case(rel.model.__name__): rel.model for rel in relations}

        model = related_model_map.get(key)
        if model is None:
            msg = f"Model '{key}' doesn't exist or have a generic relation to '{rel_info.model.__name__}'."
            raise GraphQLInvalidInputDataError(msg)

        node.model = model

        match model_data:
            case dict():
                rel = node.handle_one(data=model_data)

                setattr(instance, rel_info.field_name, rel)
                self.field_names.add(rel_info.field_name)  # type: ignore[arg-type]

            case None:
                if not rel_info.related_nullable:
                    raise GraphQLRelationNotNullableError(field_name=rel_info.field_name, model=self.model)

                setattr(instance, rel_info.field_name, None)
                self.field_names.add(rel_info.field_name)  # type: ignore[arg-type]

            case _:
                raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=model_data)

        self.put_before(node, field_name=rel_info.field_name, related_name=rel_info.related_name)  # type: ignore[arg-type]

    def _disconnect_instances(self, instances: set[Model], rel_info: RelInfo, node: MutationNode) -> None:
        """
        Disconnect instances for:

        - reverse one-to-one, if the relation is updated to another instance
        - reverse foreign keys relations, if a some of the instances are not updated or picked using pk.

        Do not allow disconnecting if the forward relation is not nullable.
        """
        if not rel_info.related_nullable:
            raise GraphQLRelationNotNullableError(field_name=rel_info.related_name, model=node.model)

        disconnect_node = MutationNode(model=rel_info.related_model, related_action=self.related_action)  # type: ignore[arg-type]

        for instance in instances:
            setattr(instance, rel_info.related_name, None)  # type: ignore[arg-type]
            disconnect_node.instances.append(instance)
            disconnect_node.field_names.add(rel_info.related_name)  # type: ignore[arg-type]

        # For reverse one-to-one relations, existing relation must be disconnected before new relation is added
        # to satisfy on-to-one constraint.
        node.put_before(
            disconnect_node,
            field_name=f"__disconnect_old_{rel_info.field_name}",
            related_name=f"__connect_new_{rel_info.field_name}",
        )

    def _remove_instances(self, instances: set[Model], rel_info: RelInfo, node: MutationNode) -> None:
        """Remove the given related instances when a relation is updated."""
        remove_node = MutationNode(model=rel_info.related_model, related_action=self.related_action)  # type: ignore[arg-type]
        remove_node.instances.extend(instances)
        remove_node.mutation_func = remove_node.mutate_delete

        # For reverse one-to-one relations, existing relation must be removed before new relation is added
        # to satisfy on-to-one constraint.
        node.put_before(
            remove_node,
            field_name=f"__remove_old_{rel_info.field_name}",
            related_name=f"__add_new_{rel_info.field_name}",
        )

    # Link handling

    def merge(self, node: MutationNode, *, previous_node: MutationNode | None = None) -> Self:
        """Merge the given MutationNode into this one."""
        if node.model != self.model:
            raise GraphQLMutationTreeModelMismatchError(model_1=node.model, model_2=self.model)

        self.instances.extend(node.instances)

        for name, before_node in self.before.items():
            if previous_node == before_node:
                continue

            other_before_node = node.before.get(name)
            if other_before_node is not None:
                before_node.merge(other_before_node, previous_node=self)

        for name, after_node in self.after.items():
            if previous_node == after_node:
                continue

            other_after_node = node.after.get(name)
            if other_after_node is not None:
                after_node.merge(other_after_node, previous_node=self)

        return self

    def put_before(self, node: MutationNode, *, field_name: str, related_name: str) -> Self:
        """Put the given MutationNode before the current one."""
        before_node = self.before.get(field_name)
        if before_node is not None:
            before_node.merge(node)
            return self

        self.before[field_name] = node
        node.after[related_name] = self
        return self

    def put_after(self, node: MutationNode, *, field_name: str, related_name: str) -> Self:
        """Put the given MutationNode after the current one."""
        after_node = self.after.get(field_name)
        if after_node is not None:
            after_node.merge(node)
            return self

        self.after[field_name] = node
        node.before[related_name] = self
        return self

    # Through model handling

    def _remove_through(
        self,
        through_map: defaultdict[Model, dict[Model, Model]],
        *,
        source_name: str,
        target_name: str,
        reverse: bool,
        symmetrical: bool,
    ) -> None:
        """Remove through model instances."""
        not_updated = Q()
        for source, target_map in through_map.items():
            not_updated |= Q(**{source_name: source}) & ~Q(**{f"{target_name}__in": list(target_map)})
            if symmetrical:
                not_updated |= Q(**{target_name: source}) & ~Q(**{f"{source_name}__in": list(target_map)})

        pks: set[Any] = set()
        source_to_removed_target_pks: defaultdict[Model, set[Any]] = defaultdict(set)

        qs = get_default_manager(self.model).filter(not_updated).select_related(source_name, target_name)

        for through_instance in qs:
            source = getattr(through_instance, source_name)
            target = getattr(through_instance, target_name)
            source_to_removed_target_pks[source].add(target.pk)
            pks.add(through_instance.pk)

        # If there are no through instances to remove, we can skip the rest
        if not pks:
            return

        with use_m2m_remove_signals(
            model=self.model,
            source_to_removed_target_pks=source_to_removed_target_pks,
            target_name=target_name,
            reverse=reverse,
        ):
            get_default_manager(self.model).filter(pk__in=pks).delete()

    def _upsert_through(
        self,
        through_map: defaultdict[Model, dict[Model, Model]],
        *,
        source_name: str,
        target_name: str,
        reverse: bool,
        symmetrical: bool,
    ) -> None:
        """Add or update through model instances."""
        # If there are no through instances, we can skip the upsert
        if not through_map:
            return

        if symmetrical:
            self._backfill_symmetrical(
                through_map,
                source_name=source_name,
                target_name=target_name,
            )

        self._use_existing_through(
            through_map,
            source_name=source_name,
            target_name=target_name,
            symmetrical=symmetrical,
        )

        instances: list[Model] = []
        source_to_added_target_pks: defaultdict[Model, set[Any]] = defaultdict(set)

        for source, target_map in through_map.items():
            for target, instance in target_map.items():
                instances.append(instance)
                # Send signals only for added instances, not for updated existing ones
                if instance.pk is None:
                    source_to_added_target_pks[source].add(target.pk)

        kwargs = get_bulk_create_kwargs(self.model, *self.field_names)

        with use_m2m_add_signals(
            model=self.model,
            source_to_added_target_pks=source_to_added_target_pks,
            target_name=target_name,
            reverse=reverse,
        ):
            get_default_manager(self.model).bulk_create(objs=instances, **kwargs)

    def _backfill_symmetrical(
        self,
        through_map: defaultdict[Model, dict[Model, Model]],
        *,
        source_name: str,
        target_name: str,
    ) -> None:
        """Add symmetrical instances to the 'through_map'."""
        symmetric_map: defaultdict[Model, dict[Model, Model]] = defaultdict(dict)

        field_names = {field.name for field in self.model._meta.get_fields()}
        field_names.discard(self.model._meta.pk.name)
        field_names.discard(source_name)
        field_names.discard(target_name)

        for source, target_map in through_map.items():
            for target, instance in target_map.items():
                symmetrical_instance = self.model()
                setattr(symmetrical_instance, source_name, target)
                setattr(symmetrical_instance, target_name, source)

                for field_name in field_names:
                    setattr(symmetrical_instance, field_name, getattr(instance, field_name))

                symmetric_map[target][source] = symmetrical_instance

        for target, source_map in symmetric_map.items():
            for source, instance in source_map.items():
                through_map[target][source] = instance

    def _use_existing_through(
        self,
        through_map: defaultdict[Model, dict[Model, Model]],
        *,
        source_name: str,
        target_name: str,
        symmetrical: bool,
    ) -> None:
        """
        Replace new instances in the 'through_map' with existing through model instances
        that have the same source and target.
        """
        existing = Q()
        for source, target_map in through_map.items():
            existing |= Q(**{source_name: source, f"{target_name}__in": list(target_map)})
            if symmetrical:
                existing |= Q(**{target_name: source, f"{source_name}__in": list(target_map)})

        qs = get_default_manager(self.model).filter(existing).select_related(source_name, target_name)

        field_names = {field.name for field in self.model._meta.get_fields()}
        field_names.discard(self.model._meta.pk.name)
        field_names.discard(source_name)
        field_names.discard(target_name)

        for through_instance in qs:
            source = getattr(through_instance, source_name)
            target = getattr(through_instance, target_name)

            new_through_instance = through_map[source][target]
            for field_name in field_names:
                setattr(through_instance, field_name, getattr(new_through_instance, field_name))

            through_map[source][target] = through_instance
