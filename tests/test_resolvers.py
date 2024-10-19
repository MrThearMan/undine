from typing import Any

import pytest
from django.db import models
from graphql import GraphQLResolveInfo

from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo, exact
from undine.errors.exceptions import GraphQLInvalidManyRelatedFieldError
from undine.resolvers import FunctionResolver, ModelFieldResolver, ModelManyRelatedResolver
from undine.typing import GQLInfo


@pytest.mark.django_db
def test_model_field_resolver():
    resoler = ModelFieldResolver("name")

    task = TaskFactory.create(name="Test task")

    assert resoler(model=task, info=MockGQLInfo()) == "Test task"


@pytest.mark.django_db
def test_model_field_resolver__doesnt_exist():
    resoler = ModelFieldResolver("foo")

    task = TaskFactory.create(name="Test task")

    assert resoler(model=task, info=MockGQLInfo()) is None


@pytest.mark.django_db
def test_model_many_related_resolver():
    resoler = ModelManyRelatedResolver("assignees")

    task = TaskFactory.create(assignees__name="Assignee")

    result = resoler(model=task, info=MockGQLInfo())

    assert isinstance(result, models.QuerySet)
    assert result.count() == 1
    assignee = result.first()
    assert assignee.name == "Assignee"


@pytest.mark.django_db
def test_model_many_related_resolver__doesnt_exist():
    resoler = ModelManyRelatedResolver("foo")

    task = TaskFactory.create(assignees__name="Assignee")

    msg = (
        "Trying to resolve field 'foo' on model 'example_project.app.models.Task' as a many-related field, "
        "but field doesn't resolve into a related manager. Got 'None' instead."
    )
    with pytest.raises(GraphQLInvalidManyRelatedFieldError, match=exact(msg)):
        resoler(model=task, info=MockGQLInfo())


def test_function_resolver():
    def func():
        return "foo"

    resoler = FunctionResolver(func)
    result = resoler(root=None, info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__root():
    def func(root: Any):
        return root

    resoler = FunctionResolver(func, root_param="root")
    result = resoler(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__info():
    def func(info: GQLInfo):
        return info

    info = MockGQLInfo()
    resoler = FunctionResolver(func, info_param="info")
    result = resoler(root=None, info=info)
    assert result == info


def test_function_resolver__adapt():
    def func():
        return "foo"

    resoler = FunctionResolver.adapt(func)
    result = resoler(root=None, info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__adapt__root():
    def func(root: Any):
        return root

    resoler = FunctionResolver.adapt(func)
    result = resoler(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__adapt__root__self():
    def func(self: Any):
        return self

    resoler = FunctionResolver.adapt(func)
    result = resoler(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__adapt__root__cls():
    def func(cls: Any):
        return cls

    resoler = FunctionResolver.adapt(func)
    result = resoler(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_function_resolver__adapt__info():
    def func(info: GQLInfo):
        return info

    info = MockGQLInfo()
    resoler = FunctionResolver.adapt(func)
    result = resoler(root=None, info=info)
    assert result == info


def test_function_resolver__adapt__info__graphql_resolver_info():
    def func(info: GraphQLResolveInfo):
        return info

    info = MockGQLInfo()
    resoler = FunctionResolver.adapt(func)
    result = resoler(root=None, info=info)
    assert result == info
