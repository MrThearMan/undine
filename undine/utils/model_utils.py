from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeGuard

from django.core.exceptions import FieldDoesNotExist
from django.db.models import F, Field, IntegerField, Model, Subquery
from django.db.models.constants import LOOKUP_SEP

from undine.errors.exceptions import (
    ExpessionMultipleOutputFieldError,
    ExpessionNoOutputFieldError,
    GraphQLModelNotFoundError,
    GraphQLMultipleObjectsFoundError,
    ModelFieldDoesNotExistError,
    ModelFieldNotARelationError,
)

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    from undine.typing import CombinableExpression, ModelField, TModel, ToManyField, ToOneField

__all__ = [
    "SubqueryCount",
    "determine_output_field",
    "generic_foreign_key_for_generic_relation",
    "generic_relations_for_generic_foreign_key",
    "get_instance_or_raise",
    "get_model_field",
    "get_model_fields_for_graphql",
    "get_model_update_fields",
    "is_to_many",
    "is_to_one",
]


def get_instance_or_raise(*, model: type[TModel], key: str, value: Any) -> TModel:
    """Get model by the given key with the given value. Raise GraphQL errors appropriately."""
    try:
        return model._meta.default_manager.get(**{key: value})
    except model.DoesNotExist as error:
        raise GraphQLModelNotFoundError(key=key, value=value, model=model) from error
    except model.MultipleObjectsReturned as error:
        raise GraphQLMultipleObjectsFoundError(key=key, value=value, model=model) from error


def generic_relations_for_generic_foreign_key(fk: GenericForeignKey) -> Generator[GenericRelation, None, None]:
    """Get all GenericRelations for the given GenericForeignKey."""
    from django.contrib.contenttypes.fields import GenericRelation  # noqa: PLC0415

    return (field for field in fk.model._meta._relation_tree if isinstance(field, GenericRelation))


def generic_foreign_key_for_generic_relation(relation: GenericRelation) -> GenericForeignKey:
    """Get the GenericForeignKey for the given GenericRelation."""
    from django.contrib.contenttypes.fields import GenericForeignKey  # noqa: PLC0415

    return next(
        field
        for field in relation.related_model._meta.get_fields()
        if (
            isinstance(field, GenericForeignKey)
            and field.fk_field == relation.object_id_field_name
            and field.ct_field == relation.content_type_field_name
        )
    )


def get_model_field(*, model: type[Model], lookup: str) -> ModelField:
    """
    Gets a model field from the given lookup string.

    :param model: Django model to start finding the field from.
    :param lookup: Lookup string using Django's lookup syntax. E.g. "foo__bar__baz".
    """
    parts = lookup.split(LOOKUP_SEP)
    last = len(parts)
    field: Field | None = None

    for part_num, part in enumerate(parts, start=1):
        if part == "pk":
            field = model._meta.pk
        else:
            try:
                field = model._meta.get_field(part)
            except FieldDoesNotExist as error:
                if not part.endswith("_set"):
                    raise ModelFieldDoesNotExistError(field=part, model=model) from error

                # Field might be a reverse many-related field without `related_name`, in which case
                # the `model._meta.fields_map` will store the relation without the "_set" suffix.
                try:
                    field = model._meta.get_field(part.removesuffix("_set"))
                except FieldDoesNotExist as error:
                    raise ModelFieldDoesNotExistError(field=part, model=model) from error

        if part_num == last:
            break

        if not field.is_relation:
            raise ModelFieldNotARelationError(field=part, model=model)

        model = field.related_model

    if field is None:  # pragma: no cover
        raise ModelFieldDoesNotExistError(field=lookup, model=model) from None

    return field


def get_model_fields_for_graphql(
    model: type[Model],
    *,
    include_relations: bool = True,
    include_nonsaveable: bool = True,
) -> Generator[Field, None, None]:
    """
    Get all fields from the model that should be included in a GraphQL schema.

    :param model: The model to get fields from.
    :param include_relations: Whether to include relation fields.
    :param include_nonsaveable: Whether to include fields that are not editable or not concrete.
    """
    for model_field in model._meta._get_fields():
        is_relation = bool(getattr(model_field, "is_relation", False))  # Does field reference a relation?
        editable = bool(getattr(model_field, "editable", True))  # Is field value editable by users?
        concrete = bool(getattr(model_field, "concrete", True))  # Does field correspond to a db column?

        if is_relation:
            if include_relations:
                yield model_field
            continue

        if not include_nonsaveable and (not editable or not concrete):
            continue

        yield model_field


def get_model_update_fields(model: type[Model], *fields: str) -> Iterable[str] | None:
    # 'GenericForeignKey' fields or 'pk' properties cannot be in the 'update_fields' set.
    # If they are, we cannot optimize the update to only the fields actually updated.
    if set(fields).issubset(model._meta._non_pk_concrete_field_names):
        return fields
    return None


def is_to_many(field: Field) -> TypeGuard[ToManyField]:
    return bool(field.one_to_many or field.many_to_many)


def is_to_one(field: Field) -> TypeGuard[ToOneField]:
    return bool(field.many_to_one or field.one_to_one)


class SubqueryCount(Subquery):
    """
    Count to-many related objects using a subquery.
    Should be used instead of "models.Count" when there might be collisions
    between counted related objects and filter conditions.

    >>> class Foo(Model):
    >>>     number = IntegerField()
    >>>
    >>> class Bar(Model):
    >>>     number = IntegerField()
    >>>     example = ForeignKey(Foo, on_delete=CASCADE, related_name="bars")
    >>>
    >>> foo = Foo.objects.create(number=1)
    >>> Bar.objects.create(example=foo, number=2)
    >>> Bar.objects.create(example=foo, number=2)
    >>>
    >>> foo = (
    >>>     Foo.objects.annotate(count=Count("bars"))
    >>>     .filter(bars__number=2)
    >>>     .first()
    >>> )
    >>> assert foo.count == 2

    This fails and asserts that count is 4. The reason is that Bar objects are
    joined twice: once for the count, and once for the filter. Django does not
    reuse the join, since it is not aware that the join is the same.

    Therefore, do this instead:

    >>> foo = (
    >>>     Foo.objects.annotate(
    >>>         count=SubqueryCount(
    >>>             Bar.objects.filter(example=OuterRef("example")),
    >>>         ),
    >>>     )
    >>>     .filter(bars__number=2)
    >>>     .first()
    >>> )
    """

    template = "(SELECT COUNT(*) FROM (%(subquery)s) _count)"
    output_field = IntegerField()

    def __repr__(self) -> str:
        try:
            subquery = str(self.query)
        except Exception:  # noqa: BLE001
            subquery = "<subquery>"
        return f"<{self.__class__.__name__}{self.template % {'subquery': subquery}}>"


def determine_output_field(expression: CombinableExpression, *, model: type[Model]) -> None:  # TODO: Test
    """Determine the `output_field` for the given expression if it doesn't have one."""
    if hasattr(expression, "output_field"):
        return

    possible_output_fields: dict[type[Field], Any] = {}
    for expr in expression.get_source_expressions():
        if hasattr(expr, "output_field"):
            field: Field = expr.output_field
            possible_output_fields[field.__class__] = field.clone()
            continue

        if isinstance(expr, F):
            field: Field = get_model_field(model=model, lookup=expr.name)
            possible_output_fields[field.__class__] = field.clone()
            continue

    if len(possible_output_fields) == 0:
        raise ExpessionNoOutputFieldError(expr=expression)

    if len(possible_output_fields) > 1:
        raise ExpessionMultipleOutputFieldError(expr=expression, output_fields=possible_output_fields)

    expression.output_field = next(iter(possible_output_fields.values()))
