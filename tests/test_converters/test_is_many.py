from __future__ import annotations

from typing import Any, NamedTuple, TypedDict

import pytest
from django.db.models import CharField, F, Q, QuerySet, Subquery, Value
from django.db.models.functions import Now

from example_project.app.models import Comment, Person, Project, Task
from tests.helpers import parametrize_helper
from undine import Calculation, CalculationArgument, DjangoExpression, GQLInfo, MutationType, QueryType
from undine.converters import is_many
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, TypeRef
from undine.exceptions import ModelFieldNotARelationOfModelError


class Params(NamedTuple):
    value: Any
    expected: bool


def func_1() -> list: ...
def func_2() -> list[str]: ...
def func_3() -> str: ...
def func_4() -> set: ...
def func_5() -> tuple: ...
def func_6() -> QuerySet: ...


class Arguments(TypedDict):
    value: int


@pytest.mark.parametrize(
    **parametrize_helper({
        "func list": Params(
            value=func_1,
            expected=True,
        ),
        "func list generic": Params(
            value=func_2,
            expected=True,
        ),
        "func str": Params(
            value=func_3,
            expected=False,
        ),
        "func set": Params(
            value=func_4,
            expected=True,
        ),
        "func tuple": Params(
            value=func_5,
            expected=True,
        ),
        "func queryset": Params(
            value=func_6,
            expected=True,
        ),
        "model field": Params(
            value=CharField(max_length=255),
            expected=False,
        ),
        "foreign key": Params(
            value=Task._meta.get_field("project"),
            expected=False,
        ),
        "many to many field": Params(
            value=Task._meta.get_field("assignees"),
            expected=True,
        ),
        "reverse foreign key": Params(
            value=Task._meta.get_field("steps"),
            expected=True,
        ),
        "reverse many to many field": Params(
            value=Task._meta.get_field("reports"),
            expected=True,
        ),
        "generic relation": Params(
            value=Task._meta.get_field("comments"),
            expected=True,
        ),
        "generic foreign key": Params(
            value=Comment._meta.get_field("target"),
            expected=False,
        ),
        "expression": Params(
            value=Now(),
            expected=False,
        ),
        "f-expression": Params(
            value=F("name"),
            expected=False,
        ),
        "q-expression": Params(
            value=Q(name="foo"),
            expected=False,
        ),
        "subquery": Params(
            value=Subquery(Task.objects.values("id")),
            expected=False,
        ),
        "lazy_union": Params(
            value=LazyGenericForeignKey(field=Comment._meta.get_field("target")),
            expected=False,
        ),
        "type ref": Params(
            value=TypeRef(int),
            expected=False,
        ),
        "type ref list": Params(
            value=TypeRef(list),
            expected=True,
        ),
        "type ref list generic": Params(
            value=TypeRef(list[int]),
            expected=True,
        ),
        "type ref set": Params(
            value=TypeRef(set),
            expected=True,
        ),
        "type ref tuple": Params(
            value=TypeRef(tuple),
            expected=True,
        ),
        "type ref queryset": Params(
            value=TypeRef(QuerySet),
            expected=True,
        ),
    }),
)
def test_is_many(value, expected) -> None:
    assert is_many(value) is expected


def test_is_many__calculated() -> None:
    class ExampleCalculation(Calculation[int | None]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert is_many(ExampleCalculation) is False


def test_is_many__calculated__list() -> None:
    class ExampleCalculation(Calculation[list[int]]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value([self.value])

    assert is_many(ExampleCalculation) is True


def test_is_many__lazy_query_type__foreign_key() -> None:
    class ProjectType(QueryType[Project]): ...

    field = Task._meta.get_field("project")
    lazy = LazyRelation(field=field)

    assert is_many(lazy) is False


def test_is_many__lazy_query_type__many_to_many() -> None:
    class AssigneeType(QueryType[Person]): ...

    field = Task._meta.get_field("assignees")
    lazy = LazyRelation(field=field)

    assert is_many(lazy) is True


def test_is_many__lazy_lambda_query_type() -> None:
    class TaskType(QueryType[Task]): ...

    lazy = LazyLambda(callback=lambda: TaskType)

    assert is_many(lazy) is False


def test_is_many__lazy_query_type_union() -> None:
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]): ...

    class CommentType(QueryType[Comment]): ...

    field = Comment._meta.get_field("target")
    lazy = LazyGenericForeignKey(field=field)

    assert is_many(lazy) is False


def test_is_many__query_type__foreign_key() -> None:
    class ProjectType(QueryType[Project]): ...

    assert is_many(ProjectType, model=Task, name="project") is False


def test_is_many__query_type__many_to_many() -> None:
    class AssigneeType(QueryType[Person]): ...

    assert is_many(AssigneeType, model=Task, name="assignees") is True


def test_is_many__mutation_type__foreign_key() -> None:
    class ProjectMutation(MutationType[Project], kind="related"): ...

    assert is_many(ProjectMutation, model=Task, name="project") is False


def test_is_many__mutation_type__many_to_many() -> None:
    class AssigneeMutation(MutationType[Person], kind="related"): ...

    assert is_many(AssigneeMutation, model=Task, name="assignees") is True


def test_is_many__mutation_type__model__single() -> None:
    assert is_many(Project, model=Task, name="project") is False


def test_is_many__mutation_type__model__many() -> None:
    assert is_many(Person, model=Task, name="assignees") is True


def test_is_many__mutation_type__model__not_correct() -> None:
    with pytest.raises(ModelFieldNotARelationOfModelError):
        assert is_many(Project, model=Task, name="assignees") is True
