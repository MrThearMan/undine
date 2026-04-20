from __future__ import annotations

import operator as op

import pytest
from django.db.models.fields.related import RelatedField

from example_project.app.models import Task
from undine.typing import ErrorUnionFieldErrorDict, ManyMatch, MutationKind, RelationType


def test_relation_type__is_single() -> None:
    assert RelationType.FORWARD_ONE_TO_ONE.is_single is True
    assert RelationType.FORWARD_MANY_TO_ONE.is_single is True
    assert RelationType.FORWARD_MANY_TO_MANY.is_single is False


def test_relation_type__is_many() -> None:
    assert RelationType.FORWARD_MANY_TO_MANY.is_many is True
    assert RelationType.REVERSE_ONE_TO_MANY.is_many is True
    assert RelationType.FORWARD_ONE_TO_ONE.is_many is False


def test_relation_type__is_reverse() -> None:
    assert RelationType.REVERSE_ONE_TO_ONE.is_reverse is True
    assert RelationType.FORWARD_ONE_TO_ONE.is_reverse is False


def test_relation_type__is_forward() -> None:
    assert RelationType.FORWARD_ONE_TO_ONE.is_forward is True
    assert RelationType.REVERSE_ONE_TO_ONE.is_forward is False


def test_relation_type__is_generic_relation() -> None:
    assert RelationType.GENERIC_ONE_TO_MANY.is_generic_relation is True
    assert RelationType.FORWARD_ONE_TO_ONE.is_generic_relation is False


def test_relation_type__is_generic_foreign_key() -> None:
    assert RelationType.GENERIC_MANY_TO_ONE.is_generic_foreign_key is True
    assert RelationType.FORWARD_ONE_TO_ONE.is_generic_foreign_key is False


def test_relation_type__is_many_to_many() -> None:
    assert RelationType.FORWARD_MANY_TO_MANY.is_many_to_many is True
    assert RelationType.REVERSE_MANY_TO_MANY.is_many_to_many is True
    assert RelationType.FORWARD_ONE_TO_ONE.is_many_to_many is False


def test_relation_type__for_related_field() -> None:
    fk_field = Task._meta.get_field("project")
    assert RelationType.for_related_field(fk_field) == RelationType.FORWARD_MANY_TO_ONE

    reverse_field = Task._meta.get_field("acceptancecriteria")
    assert RelationType.for_related_field(reverse_field) == RelationType.REVERSE_ONE_TO_MANY


def test_relation_type__for_related_field__unknown() -> None:
    class UnknownRelatedField(RelatedField): ...

    field = UnknownRelatedField.__new__(UnknownRelatedField)

    with pytest.raises(ValueError, match="Unknown related field"):
        RelationType.for_related_field(field)


def test_mutation_kind__requires_pk() -> None:
    assert MutationKind.update.requires_pk is True
    assert MutationKind.delete.requires_pk is True
    assert MutationKind.create.requires_pk is False


def test_mutation_kind__no_pk() -> None:
    assert MutationKind.create.no_pk is True
    assert MutationKind.custom.no_pk is True
    assert MutationKind.update.no_pk is False


def test_mutation_kind__should_use_autogeneration() -> None:
    assert MutationKind.create.should_use_autogeneration is True
    assert MutationKind.update.should_use_autogeneration is True
    assert MutationKind.related.should_use_autogeneration is True
    assert MutationKind.delete.should_use_autogeneration is False


def test_mutation_kind__should_include_default_value() -> None:
    assert MutationKind.create.should_include_default_value is True
    assert MutationKind.update.should_include_default_value is False


def test_mutation_kind__all_inputs_used_by_default() -> None:
    assert MutationKind.custom.all_inputs_used_by_default is True
    assert MutationKind.create.all_inputs_used_by_default is False


def test_many_match__operator__any() -> None:
    assert ManyMatch.any.operator is op.or_


def test_many_match__operator__all() -> None:
    assert ManyMatch.all.operator is op.and_


def test_many_match__operator__one_of() -> None:
    assert ManyMatch.one_of.operator is op.xor


def test_error_union_field_error_dict() -> None:
    err = ValueError("test")
    d = ErrorUnionFieldErrorDict({"key": "value"}, error=err)
    assert d.error is err
    assert d["key"] == "value"
