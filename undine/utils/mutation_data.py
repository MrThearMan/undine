from __future__ import annotations

import dataclasses
from collections import defaultdict
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, overload

from django.db.models import Model
from django.db.models.manager import BaseManager
from graphql import Undefined

from undine.exceptions import (
    GraphQLInvalidInputDataError,
    GraphQLMutationInputNotFoundError,
    GraphQLMutationInstanceLimitError,
)
from undine.parsers import parse_model_relation_info
from undine.settings import undine_settings
from undine.typing import RelatedAction

from .model_utils import generic_relations_for_generic_foreign_key, get_instances_or_raise
from .reflection import is_list_of, is_subclass
from .text import to_camel_case

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine import MutationType
    from undine.dataclasses import RelInfo

__all__ = [
    "MutationData",
    "get_mutation_data",
]


Placements: TypeAlias = defaultdict[type[Model], dict[tuple[str | int, ...], Any]]


@overload
def get_mutation_data(
    *,
    model: type[Model],
    data: dict[str, Any],
    mutation_type: type[MutationType] | None = None,
) -> MutationData: ...


@overload
def get_mutation_data(
    *,
    model: type[Model],
    data: list[dict[str, Any]],
    mutation_type: type[MutationType] | None = None,
) -> list[MutationData]: ...


def get_mutation_data(
    *,
    model: type[Model],
    data: dict[str, Any] | list[dict[str, Any]],
    mutation_type: type[MutationType] | None = None,
) -> MutationData | list[MutationData]:
    if single := isinstance(data, dict):
        data = [data]

    mutation_data = build_mutation_data(model=model, data=data, mutation_type=mutation_type)

    if single:
        return mutation_data[0]
    return mutation_data


def build_mutation_data(
    *,
    model: type[Model],
    data: list[dict[str, Any]],
    mutation_type: type[MutationType] | None = None,
) -> list[MutationData]:
    mutation_infos = [get_mutation_info(model=model, data=item) for item in data]

    instance_count = sum(mutation_info.instance_count for mutation_info in mutation_infos)
    if instance_count > undine_settings.MUTATION_INSTANCE_LIMIT:
        raise GraphQLMutationInstanceLimitError(limit=undine_settings.MUTATION_INSTANCE_LIMIT, count=instance_count)

    placements: Placements = defaultdict(dict)

    for i, mutation_info in enumerate(mutation_infos):
        get_placements(placements, data=mutation_info, path=[i])

    for path_model, path_to_pk in placements.items():
        pks = set(path_to_pk.values())

        # TODO: Could join required relations. Should still check that fetched instance count is correct.
        instances = get_instances_or_raise(model=path_model, pks=pks)
        instances_map = {instance.pk: instance for instance in instances}

        for path, pk in path_to_pk.items():
            obj: Any = mutation_infos
            for key in path:
                obj = obj[key]

            mut_info: MutationInfo = obj
            mut_info.instance = instances_map[pk]

    return [mutation_info.process(mutation_type) for mutation_info in mutation_infos]


def get_placements(placements: Placements, *, data: MutationInfo, path: list[str | int]) -> None:
    if "pk" in data.fields:
        placements[data.model][tuple(path)] = data.fields["pk"]

    for key, single_data in data.single_relations.items():
        if single_data is not None:
            get_placements(placements, data=single_data, path=[*path, "single_relations", key])

    for key, many_data in data.many_relations.items():
        for i, item_data in enumerate(many_data):
            get_placements(placements, data=item_data, path=[*path, "many_relations", key, i])


def get_mutation_info(*, model: type[Model], data: dict[str, Any]) -> MutationInfo:
    relation_info = parse_model_relation_info(model=model)

    fields: dict[str, Any] = {}
    single_relations: dict[str, MutationInfo | None] = {}
    many_relations: dict[str, list[MutationInfo]] = {}

    for field_name, field_data in data.items():
        rel_info = relation_info.get(field_name)
        if rel_info is None:
            fields[field_name] = field_data
            continue

        # Generic foreign key
        if rel_info.relation_type.is_generic_foreign_key:
            single_relations[field_name] = get_generic_foreign_key_info(data=field_data, rel_info=rel_info)
            continue

        # Single relations
        if rel_info.relation_type.is_single:
            single_relations[field_name] = get_related_info(data=field_data, rel_info=rel_info)
            continue

        # Many relations
        values = many_relations.setdefault(field_name, [])
        for item_data in field_data or []:  # 'field_data' can be None
            mutation_info = get_related_info(data=item_data, rel_info=rel_info)
            if mutation_info is not None:
                values.append(mutation_info)

    return MutationInfo(
        instance=model(),
        model=model,
        fields=fields,
        single_relations=single_relations,
        many_relations=many_relations,
    )


def get_related_info(*, data: Any, rel_info: RelInfo) -> MutationInfo | None:
    match data:
        case dict():
            return get_mutation_info(model=rel_info.related_model, data=data)  # type: ignore[arg-type]

        case rel_info.related_model_pk_type():
            return MutationInfo(
                instance=rel_info.related_model(),  # type: ignore[misc]
                model=rel_info.related_model,  # type: ignore[arg-type]
                fields={"pk": data},
            )

        case rel_info.related_model():
            return MutationInfo(
                instance=data,
                model=rel_info.related_model,  # type: ignore[arg-type]
            )

        case None:
            # TODO: Could validate if relation is nullable?
            return None

    raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)


def get_generic_foreign_key_info(*, data: Any, rel_info: RelInfo) -> MutationInfo | None:
    if not isinstance(data, dict):
        raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

    key: str | None = next(iter(data), None)
    if key is None:
        raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=data)

    model_data = data[key]

    field: GenericForeignKey = rel_info.model._meta.get_field(rel_info.field_name)  # type: ignore[assignment]
    relations = generic_relations_for_generic_foreign_key(field)
    related_model_map = {to_camel_case(rel.model.__name__): rel.model for rel in relations}

    model = related_model_map.get(key)
    if model is None:
        msg = f"Model '{key}' doesn't exist or have a generic relation to '{rel_info.model.__name__}'."
        raise GraphQLInvalidInputDataError(msg)

    match model_data:
        case dict():
            return get_mutation_info(model=model, data=model_data)

        case None:
            # TODO: Could validate if relation is nullable?
            return None

    raise GraphQLInvalidInputDataError(field_name=rel_info.field_name, data=model_data)


@dataclasses.dataclass(kw_only=True)
class MutationInfo:
    instance: Model
    model: type[Model]
    fields: dict[str, Any] = dataclasses.field(default_factory=dict)
    single_relations: dict[str, MutationInfo | None] = dataclasses.field(default_factory=dict)
    many_relations: dict[str, list[MutationInfo]] = dataclasses.field(default_factory=dict)

    def __getitem__(self, key: Literal["single_relations", "many_relations"]) -> Any:
        # For setting instances
        try:
            return getattr(self, key)
        except AttributeError as error:
            raise KeyError(key) from error

    @property
    def instance_count(self) -> int:
        instance_count = 1

        for single_data in self.single_relations.values():
            if single_data is not None:
                instance_count += single_data.instance_count

        for many_data in self.many_relations.values():
            for item_data in many_data:
                instance_count += item_data.instance_count

        return instance_count

    def process(self, mutation_type: type[MutationType] | None) -> MutationData:
        data = deepcopy(self.fields)
        related_action = mutation_type.__related_action__ if mutation_type is not None else RelatedAction.null

        for key, single_data in self.single_relations.items():
            sub_mutation_type = get_nested_mutation_type(mutation_type=mutation_type, field_name=key)
            data[key] = single_data.process(sub_mutation_type) if single_data is not None else None

        for key, many_data in self.many_relations.items():
            values = data.setdefault(key, [])
            sub_mutation_type = get_nested_mutation_type(mutation_type=mutation_type, field_name=key)
            for item_data in many_data:
                values.append(item_data.process(sub_mutation_type))

        return MutationData(instance=self.instance, data=data, related_action=related_action)


@dataclasses.dataclass(kw_only=True)
class MutationData:
    """Processed data that everything needed to mutate the given instance."""

    instance: Model
    """The instance that the data will be applied to."""

    data: dict[str, Any]  # Node: `Any` can be `MutationData` or `list[MutationData]`
    """The data that will be applied to the instance as part of this mutation."""

    related_action: RelatedAction
    """If this is a related mutation, what action should be taken on non-updated related objects."""

    @property
    def plain_data(self) -> dict[str, Any]:
        """Plain data without additional information."""
        data: dict[str, Any] = {}

        for key, value in self.data.items():
            if isinstance(value, MutationData):
                data[key] = value.plain_data
                continue

            if is_list_of(value, MutationData):
                data[key] = [item.plain_data for item in value]
                continue

            data[key] = value

        return data

    @property
    def previous_data(self) -> dict[str, Any]:
        """What data will will change in the given instance if this mutation is performed."""
        if self.instance.pk is None:
            return {}

        data: dict[str, Any] = {}
        for key, value in self.data.items():
            if isinstance(value, MutationData):
                data[key] = value.previous_data
                continue

            if is_list_of(value, MutationData):
                data[key] = [item.previous_data for item in value]
                continue

            previous_value = getattr(self.instance, key, Undefined)
            if previous_value == Undefined:
                continue

            if isinstance(previous_value, BaseManager):
                previous_value = list(previous_value.all())

            data[key] = previous_value

        return data


def get_nested_mutation_type(mutation_type: type[MutationType] | None, field_name: str) -> type[MutationType] | None:
    if mutation_type is None:
        return None

    input_field = mutation_type.__input_map__.get(field_name)

    if input_field is None:  # pragma: no cover
        raise GraphQLMutationInputNotFoundError(field_name=field_name, mutation_type=mutation_type)

    from undine import MutationType  # noqa: PLC0415

    if is_subclass(input_field.ref, MutationType):
        return input_field.ref

    return None
