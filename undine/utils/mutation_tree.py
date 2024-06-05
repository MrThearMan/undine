from __future__ import annotations

import dataclasses
from collections import defaultdict
from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING, Any, Self, overload

from django.db import router, transaction  # noqa: ICN003
from django.db.models import Q
from django.db.models.signals import m2m_changed, post_save, pre_save
from graphql import GraphQLError, GraphQLResolveInfo, Undefined

from undine.exceptions import (
    GraphQLErrorGroup,
    GraphQLInvalidInputDataError,
    GraphQLModelConstraintViolationError,
    GraphQLMutationInputNotFoundError,
    GraphQLMutationInstanceLimitError,
    GraphQLMutationTreeModelMismatchError,
    GraphQLRelationNotNullableError,
)
from undine.parsers import parse_model_relation_info
from undine.settings import undine_settings
from undine.typing import RelationType
from undine.utils.model_utils import (
    convert_integrity_errors,
    generic_relations_for_generic_foreign_key,
    get_bulk_create_kwargs,
    get_default_manager,
    get_instance_or_raise,
    get_instances_or_raise,
    set_forward_ids,
)
from undine.utils.reflection import is_subclass
from undine.utils.text import to_camel_case, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Iterator

    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.db.models import Model
    from django.db.models.fields.related_descriptors import ForeignKeyDeferredAttribute, ManyToManyDescriptor

    from undine import MutationType
    from undine.dataclasses import RelInfo
    from undine.typing import GQLInfo, TModel

__all__ = [
    "mutate",
]


@overload
def mutate(
    data: dict[str, Any],
    *,
    model: type[TModel],
    info: GQLInfo | None = None,
    mutation_type: type[MutationType] | None = None,
) -> TModel: ...


@overload
def mutate(
    data: list[dict[str, Any]],
    *,
    model: type[TModel],
    info: GQLInfo | None = None,
    mutation_type: type[MutationType] | None = None,
) -> list[TModel]: ...


@transaction.atomic
@convert_integrity_errors(GraphQLModelConstraintViolationError)
def mutate(
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    model: type[TModel],
    info: GQLInfo | None = None,
    mutation_type: type[MutationType] | None = None,
) -> TModel | list[TModel]:
    """Create or update models and link or unlink relations using the given data and model."""
    start_node = MutationNode(model=model, info=info, mutation_type=mutation_type)

    if isinstance(data, dict):
        start_node.handle_one(data)
        errors = start_node.flatten_errors()
        if errors:
            raise GraphQLErrorGroup(errors)

        return start_node.mutate()[0]

    start_node.handle_many(data)
    errors = start_node.flatten_errors()
    if errors:
        raise GraphQLErrorGroup(errors)

    return start_node.mutate()


class MutationMapping:
    """
    Maps keys to lists of values.

    Used to hold data that was changed during a mutation.
    Each key holds a list of values such that the same index in each values list
    corresponds to the same instance. The `generate` method can then
    be used to generate data for each instance.

    A value of `Undefined` indicates that a previous value does
    not exist for the instance. These are removed when `generator` is called.

    >>> data = MutationMapping()
    >>> data["name"] = "foo"
    >>> data["name"] = "bar"
    >>> data["name"]
    ["foo", "bar"]
    """

    def __init__(self) -> None:
        self._data: defaultdict[str, list[Any]] = defaultdict(list)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(data={self._data!r})>"

    def __getitem__(self, key: str) -> list[Any]:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key].append(value)

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def update(self, other: MutationMapping) -> None:
        """Update this mapping with the given mapping."""
        for key, values in other._data.items():
            for value in values:
                self[key] = value

    def generator(self) -> Generator[dict[str, Any], None, None]:
        """Generate data per instance, removing `Undefined` values."""
        num_of_instances = len(next(iter(self._data.values()), []))

        for i in range(num_of_instances):
            yield {key: values[i] for key, values in self._data.items() if values[i] is not Undefined}


@dataclasses.dataclass(slots=True)
class MutationNode:
    """
    A node in a tree of mutations.
    Contains instances of a model that should be updated or created.
    May link to other `MutationNodes` to create a tree of mutations
    that can be mutated efficiently.
    """

    model: type[Model]
    """The model that this node is for."""

    info: GQLInfo | None = None
    """The GraphQL info for the mutation."""

    mutation_type: type[MutationType] | None = None
    """The MutationType for the mutation."""

    mutation_func: Callable[[], list[Model]] = dataclasses.field(init=False)
    """The function that should be run to mutate the instances."""

    instances: list[Model] = dataclasses.field(default_factory=list)
    """The instances that should be updated or created."""

    previous_data: MutationMapping = dataclasses.field(default_factory=MutationMapping)
    """Fields that are updated during the mutation, and their previous values before the mutation per instance."""

    before: dict[str, MutationNode] = dataclasses.field(default_factory=dict)
    """Mutations that should be run before this one."""

    after: dict[str, MutationNode] = dataclasses.field(default_factory=dict)
    """Mutations that should be run after this one."""

    errors: list[GraphQLError] = dataclasses.field(default_factory=list)
    """Validation an permission errors that occurred before the mutation."""

    def __post_init__(self) -> None:
        self.mutation_func = self.mutate_bulk

    def flatten_errors(self, *, previous_node: MutationNode | None = None) -> list[GraphQLError]:
        """Get all errors currently in the tree."""
        errors = self.errors.copy()

        for before_node in self.before.values():
            if before_node != previous_node:
                errors += before_node.flatten_errors(previous_node=self)

        for after_node in self.after.values():
            if after_node != previous_node:
                errors += after_node.flatten_errors(previous_node=self)

        return errors

    def current_instance_count(self, *, previous_node: MutationNode | None = None) -> int:
        """How many model instances are currently in the tree."""
        instance_count = len(self.instances)

        for before_node in self.before.values():
            if before_node != previous_node:
                instance_count += before_node.current_instance_count(previous_node=self)

        for after_node in self.after.values():
            if after_node != previous_node:
                instance_count += after_node.current_instance_count(previous_node=self)

        return instance_count

    # Mutation handling

    def mutate(self, *, previous_node: MutationNode | None = None) -> Any:
        """Run the mutations starting from this node."""
        for before_node in self.before.values():
            if before_node != previous_node:
                before_node.mutate(previous_node=self)

        instances = self.mutation_func()

        if self.mutation_type is not None and self.info is not None:
            gen = self.previous_data.generator()
            for instance in instances:
                self.mutation_type.__after__(instance=instance, info=self.info, previous_data=next(gen))

        for after_node in self.after.values():
            if after_node != previous_node:
                after_node.mutate(previous_node=self)

        return instances

    def mutate_bulk(self) -> list[Model]:
        """Mutate model instances using the `queryset.bulk_create` method."""
        kwargs = get_bulk_create_kwargs(self.model, *self.previous_data)

        instances: list[Model] = []
        for instance in self.instances:
            # Only save new instances if no fields to update
            if kwargs.update_fields or instance.pk is None:
                set_forward_ids(instance)
                if undine_settings.MUTATION_FULL_CLEAN:
                    instance.full_clean()
                instances.append(instance)

        with self._with_save_signals(instances, kwargs.update_fields):
            get_default_manager(self.model).bulk_create(objs=instances, **kwargs)

        return self.instances

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

    def handle_one(self, data: dict[str, Any]) -> Self:
        """Handle data for a single object."""
        instance_count = self.current_instance_count() + 1
        if instance_count > undine_settings.MUTATION_INSTANCE_LIMIT:
            raise GraphQLMutationInstanceLimitError(limit=undine_settings.MUTATION_INSTANCE_LIMIT)

        pk = data.get("pk")

        # TODO: Optimize fetching for nested mutations
        instance = self.model() if pk is None else get_instance_or_raise(model=self.model, pk=pk)

        self.instances.append(instance)
        self.handle_data(data, instance)
        return self

    def handle_many(self, data: list[dict[str, Any]]) -> Self:
        """Handle data for many objects."""
        instance_count = self.current_instance_count() + len(data)
        if instance_count > undine_settings.MUTATION_INSTANCE_LIMIT:
            raise GraphQLMutationInstanceLimitError(limit=undine_settings.MUTATION_INSTANCE_LIMIT)

        instances: dict[Any, Model] = {}

        pks: set[int] = {item["pk"] for item in data if "pk" in item}
        if pks:
            # TODO: Optimize fetching for nested mutations
            instances = {inst.pk: inst for inst in get_instances_or_raise(model=self.model, pks=pks)}

        for index, item in enumerate(data):
            pk = item.get("pk")
            instance = instances.get(pk) or self.model()
            self.instances.append(instance)

            with self._with_child_info(index):
                self.handle_data(item, instance)

        return self

    def handle_one_pk(self, pk: Any) -> Self:
        instance = get_instance_or_raise(model=self.model, pk=pk)
        self.instances.append(instance)
        return self

    def handle_many_pk(self, pks: Iterable[Any]) -> Self:
        instances = get_instances_or_raise(model=self.model, pks=set(pks))
        self.instances.extend(instances)
        return self

    def handle_data(self, data: dict[str, Any], instance: Model) -> Self:
        relation_info = parse_model_relation_info(model=self.model)

        if self.mutation_type is not None and self.info is not None:
            try:
                self.mutation_type.__before__(instance, self.info, data)
            except GraphQLError as error:
                self.errors.append(error)
            except GraphQLErrorGroup as error:
                self.errors.extend(error.flatten())

        for field_name, field_data in data.items():
            mutation_type = self.get_nested_mutation_type(field_name)

            rel_info = relation_info.get(field_name)
            if rel_info is None:
                if instance.pk is None:
                    self.previous_data[field_name] = Undefined
                else:
                    self.previous_data[field_name] = getattr(instance, field_name, Undefined)

                setattr(instance, field_name, field_data)
                continue

            with self._with_child_info(to_schema_name(field_name)):
                node = MutationNode(model=rel_info.model, info=self.info, mutation_type=mutation_type)  # type: ignore[arg-type]
                self.handle_relation(field_data, rel_info, instance, node)

        return self

    def get_nested_mutation_type(self, field_name: str) -> type[MutationType] | None:
        if self.mutation_type is None:
            return None

        input_field = self.mutation_type.__input_map__.get(field_name)
        if input_field is None:  # pragma: no cover
            raise GraphQLMutationInputNotFoundError(field_name=field_name, mutation_type=self.mutation_type)

        from undine import MutationType  # noqa: PLC0415

        if is_subclass(input_field.ref, MutationType):
            return input_field.ref
        return None

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
                node.handle_one(data=data)

            case rel_info.related_model_pk_type():
                node.handle_one_pk(pk=data)

            case None:
                if not rel_info.nullable:
                    raise GraphQLRelationNotNullableError(field_name=rel_info.field_name, model=self.model)

                setattr(instance, rel_info.field_name, None)
                self.previous_data[rel_info.field_name] = Undefined

            case _:
                raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

        for rel in node.instances:
            setattr(instance, rel_info.field_name, rel)
            self.previous_data[rel_info.field_name] = Undefined

        self.put_before(node, field_name=rel_info.field_name, related_name=rel_info.related_name)  # type: ignore[arg-type]

    _handle_m2o = _handle_forward_o2o
    """Handle many-to-one relations for the given instance."""

    def _handle_reverse_o2o(self, data: Any, rel_info: RelInfo, instance: Model, node: MutationNode) -> None:
        """Handle reverse one-to-one relations for the given instance."""
        parent_instance: Model | None = instance
        existing_instance: Model | None = getattr(instance, rel_info.field_name, None)
        has_existing_instance = existing_instance is not None

        match data:
            case dict():
                node.handle_one(data=data)

            case rel_info.related_model_pk_type():
                node.handle_one_pk(pk=data)

            case None:
                if not rel_info.nullable:
                    raise GraphQLRelationNotNullableError(field_name=rel_info.related_name, model=node.model)

                # Make sure relation is set to null even if its not otherwise updated.
                if not node.instances and has_existing_instance:
                    node.instances.append(existing_instance)  # type: ignore[arg-type]

                parent_instance = None

            case _:
                raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

        for rel in node.instances:
            setattr(rel, rel_info.related_name, parent_instance)  # type: ignore[arg-type]
            node.previous_data[rel_info.related_name] = Undefined  # type: ignore[index]

        self.put_after(node, field_name=rel_info.field_name, related_name=rel_info.related_name)  # type: ignore[arg-type]

        # Previous relation must be disconnected (if setting the relation to null is allowed).
        if has_existing_instance and node.instances and existing_instance.pk != node.instances[0].pk:  # type: ignore[index,union-attr]
            if not rel_info.nullable:
                raise GraphQLRelationNotNullableError(field_name=rel_info.related_name, model=node.model)

            setattr(existing_instance, rel_info.related_name, None)  # type: ignore[arg-type]

            # Existing relation must be disconnected before new relation is added to satisfy on-to-one constraint.
            remove_node = MutationNode(model=rel_info.model, info=self.info, mutation_type=node.mutation_type)  # type: ignore[arg-type]
            remove_node.previous_data[rel_info.related_name] = Undefined  # type: ignore[index]
            remove_node.instances.append(existing_instance)  # type: ignore[index,arg-type]

            node.put_before(
                remove_node,
                field_name=f"__remove_old_{rel_info.field_name}",
                related_name=f"__add_new_{rel_info.field_name}",
            )

    def _handle_o2m(self, data: list[Any], rel_info: RelInfo, instance: Model, node: MutationNode) -> None:
        """Handle one-to-many relations for the given instance."""
        parent_instance: Model | None = instance
        existing_instances: set[Model] = set()
        if instance.pk is not None:
            existing_instances = set(getattr(instance, rel_info.field_name).all())

        match data:
            case [dict(), *_]:
                node.handle_many(data=data)

            case [rel_info.related_model_pk_type(), *_]:
                node.handle_many_pk(pks=data)

            case [None, *_] | [] | None:
                if not rel_info.nullable:
                    raise GraphQLRelationNotNullableError(field_name=rel_info.related_name, model=node.model)

                # Make sure all relations are set to null even if they're not otherwise updated.
                for existing_instance in existing_instances:
                    node.instances.append(existing_instance)

                parent_instance = None

            case _:
                raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

        for rel in node.instances:
            setattr(rel, rel_info.related_name, parent_instance)  # type: ignore[arg-type]
            node.previous_data[rel_info.related_name] = Undefined  # type: ignore[index,arg-type]

        # Any relations that weren't updated must be disconnected (if setting the relation to null is allowed)
        if existing_instances:
            updated_instances: set[Model] = {instance for instance in node.instances if instance.pk is not None}
            non_updated_instances: set[Model] = existing_instances - updated_instances

            if non_updated_instances:
                if not rel_info.nullable:
                    raise GraphQLRelationNotNullableError(field_name=rel_info.related_name, model=node.model)

                for existing_instance in non_updated_instances:
                    setattr(existing_instance, rel_info.related_name, None)  # type: ignore[arg-type]
                    node.instances.append(existing_instance)
                    node.previous_data[rel_info.related_name] = Undefined  # type: ignore[index]

        self.put_after(node, field_name=rel_info.field_name, related_name=rel_info.related_name)  # type: ignore[arg-type]

    def _handle_m2m(self, data: list[Any], rel_info: RelInfo, instance: Model, node: MutationNode) -> None:
        """Handle many-to-many relations for the given instance."""
        match data:
            case [dict(), *_]:
                node.handle_many(data=data)

            case [rel_info.related_model_pk_type(), *_]:
                node.handle_many_pk(pks=data)

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

        node = MutationNode(model=m2m.through, info=self.info)
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
            node.previous_data[source_name] = Undefined
            node.previous_data[target_name] = Undefined

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

        parent_model = type(instance)
        field: GenericForeignKey = parent_model._meta.get_field(rel_info.field_name)  # type: ignore[assignment]
        relations = generic_relations_for_generic_foreign_key(field)
        related_model_map = {to_camel_case(rel.model.__name__): rel.model for rel in relations}

        model = related_model_map.get(key)
        if model is None:
            msg = f"Model '{key}' doesn't exist or have a generic relation to '{parent_model.__name__}'."
            raise GraphQLInvalidInputDataError(msg)

        node.model = model

        match model_data:
            case dict():
                node.handle_one(data=model_data)

            case None:
                if not rel_info.nullable:
                    raise GraphQLRelationNotNullableError(field_name=rel_info.field_name, model=self.model)
                setattr(instance, rel_info.field_name, None)

            case _:
                raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=model_data)

        for rel in node.instances:
            setattr(instance, rel_info.field_name, rel)
            self.previous_data[rel_info.field_name] = Undefined

        self.put_before(node, field_name=rel_info.field_name, related_name=rel_info.related_name)  # type: ignore[arg-type]

    # Link handling

    def merge(self, node: MutationNode, *, previous_node: MutationNode | None = None) -> Self:
        """Merge the given MutationNode into this one."""
        if node.model != self.model:
            raise GraphQLMutationTreeModelMismatchError(model_1=node.model, model_2=self.model)

        self.instances.extend(node.instances)
        self.errors.extend(node.errors)
        self.previous_data.update(node.previous_data)

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

        with self._with_m2m_remove_signals(
            source_to_removed_target_pks,
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

        kwargs = get_bulk_create_kwargs(self.model, *self.previous_data)

        with self._with_m2m_add_signals(
            source_to_added_target_pks,
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
        for source, target_map in through_map.items():
            for target, instance in target_map.items():
                symmetrical_instance = self.model()
                setattr(symmetrical_instance, source_name, target)
                setattr(symmetrical_instance, target_name, source)

                for field in set(self.previous_data) - {source_name, target_name}:
                    setattr(symmetrical_instance, field, getattr(instance, field))

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

        for through_instance in qs:
            source = getattr(through_instance, source_name)
            target = getattr(through_instance, target_name)

            new_through_instance = through_map[source][target]
            for field in set(self.previous_data) - {source_name, target_name}:
                setattr(through_instance, field, getattr(new_through_instance, field))

            through_map[source][target] = through_instance

    # Signal handling

    @contextmanager
    def _with_save_signals(
        self,
        instances: list[Model],
        update_fields: set[str] | None,
    ) -> Generator[None, None, None]:
        if pre_save.has_listeners(self.model):
            for instance in instances:
                pre_save.send(
                    sender=self.model,
                    instance=instance,
                    raw=False,
                    using=router.db_for_write(self.model, instance=instance),
                    update_fields=list(update_fields or []),
                )

        yield

        if post_save.has_listeners(self.model):
            for instance in instances:
                post_save.send(
                    sender=self.model,
                    instance=instance,
                    created=True,
                    update_fields=list(update_fields or []),
                    raw=False,
                    using=router.db_for_write(self.model, instance=instance),
                )

    @contextmanager
    def _with_m2m_remove_signals(
        self,
        source_to_removed_target_pks: dict[Model, set[Any]],
        *,
        target_name: str,
        reverse: bool,
    ) -> Generator[None, None, None]:
        if not m2m_changed.has_listeners(self.model):
            yield
            return

        target_model = getattr(self.model, target_name).field.remote_field.model

        for source, pk_set in source_to_removed_target_pks.items():
            m2m_changed.send(
                sender=self.model,
                action="pre_remove",
                instance=source,
                reverse=reverse,
                model=target_model,
                pk_set=pk_set,
                using=router.db_for_write(self.model, instance=source),
            )

        yield

        for source, pk_set in source_to_removed_target_pks.items():
            m2m_changed.send(
                sender=self.model,
                action="post_remove",
                instance=source,
                reverse=reverse,
                model=target_model,
                pk_set=pk_set,
                using=router.db_for_write(self.model, instance=source),
            )

    @contextmanager
    def _with_m2m_add_signals(
        self,
        source_to_added_target_pks: dict[Model, set[Any]],
        *,
        target_name: str,
        reverse: bool,
    ) -> Generator[None, None, None]:
        if not m2m_changed.has_listeners(self.model):
            yield
            return

        target_model = getattr(self.model, target_name).field.remote_field.model

        for source, pk_set in source_to_added_target_pks.items():
            m2m_changed.send(
                sender=self.model,
                action="pre_add",
                instance=source,
                reverse=reverse,
                model=target_model,
                pk_set=pk_set,
                using=router.db_for_write(self.model, instance=source),
            )

        yield

        for source, pk_set in source_to_added_target_pks.items():
            m2m_changed.send(
                sender=self.model,
                action="post_add",
                instance=source,
                reverse=reverse,
                model=target_model,
                pk_set=pk_set,
                using=router.db_for_write(self.model, instance=source),
            )

    @contextmanager
    def _with_child_info(self, child_path: str | int) -> Generator[None, None, None]:
        if self.info is None:
            yield
            return

        # Only update the resolve info path to keep error messages pointing to the correct input
        parent_info = self.info

        info = GraphQLResolveInfo(
            field_name=self.info.field_name,
            field_nodes=self.info.field_nodes,
            return_type=self.info.return_type,
            parent_type=self.info.parent_type,
            path=self.info.path.add_key(child_path),
            schema=self.info.schema,
            fragments=self.info.fragments,
            root_value=self.info.root_value,
            operation=self.info.operation,
            variable_values=self.info.variable_values,
            context=self.info.context,
            is_awaitable=self.info.is_awaitable,
        )

        try:
            self.info = info  # type: ignore[assignment]
            yield
        finally:
            self.info = parent_info
