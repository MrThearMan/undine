from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from django.db import models

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo
from undine import Field, QueryType
from undine.resolvers import FunctionResolver, ModelFieldResolver, ModelManyRelatedFieldResolver

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo

    from undine.typing import GQLInfo


@pytest.mark.django_db
def test_model_field_resolver():
    class TaskType(QueryType, model=Task):
        name = Field()

    resolver = ModelFieldResolver(TaskType.name)

    task = TaskFactory.create(name="Test task")

    assert resolver(instance=task, info=MockGQLInfo()) == "Test task"


@pytest.mark.django_db
def test_model_many_related_resolver():
    class TaskType(QueryType, model=Task):
        assignees = Field()

    resolver = ModelManyRelatedFieldResolver(TaskType.assignees)

    task = TaskFactory.create(assignees__name="Assignee")

    result = resolver(instance=task, info=MockGQLInfo())

    assert isinstance(result, models.QuerySet)
    assert result.count() == 1
    assignee = result.first()
    assert assignee.name == "Assignee"


def test_function_resolver():
    def func():
        return "foo"

    resoler = FunctionResolver(func)
    result = resoler(root=None, info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__root():
    def func(root: Any):
        return root

    resolver = FunctionResolver(func, root_param="root")
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__info():
    def func(info: GQLInfo):
        return info

    info = MockGQLInfo()
    resolver = FunctionResolver(func, info_param="info")
    result = resolver(root=None, info=info)
    assert result == info


def test_function_resolver__adapt():
    def func():
        return "foo"

    resolver = FunctionResolver.adapt(func)
    result = resolver(root=None, info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__adapt__root():
    def func(root: Any):
        return root

    resolver = FunctionResolver.adapt(func)
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__adapt__root__self():
    def func(self: Any):
        return self

    resolver = FunctionResolver.adapt(func)
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__adapt__root__cls():
    def func(cls: Any):
        return cls

    resolver = FunctionResolver.adapt(func)
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__adapt__info():
    def func(info: GQLInfo):
        return info

    info = MockGQLInfo()
    resolver = FunctionResolver.adapt(func)
    result = resolver(root=None, info=info)
    assert result == info


def test_function_resolver__adapt__info__graphql_resolver_info():
    def func(info: GraphQLResolveInfo):
        return info

    info = MockGQLInfo()
    resolver = FunctionResolver.adapt(func)
    result = resolver(root=None, info=info)
    assert result == info
