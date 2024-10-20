from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from django.core.exceptions import ValidationError
from django.db import models

from example_project.app.models import ServiceRequest, Task, TaskTypeChoices
from tests.factories import ProjectFactory, ServiceRequestFactory, TaskFactory, TaskResultFactory
from tests.helpers import MockGQLInfo, exact
from undine import Input, MutationType
from undine.errors.exceptions import (
    GraphQLInvalidManyRelatedFieldError,
    GraphQLMissingLookupFieldError,
    GraphQLModelConstaintViolationError,
    GraphQLModelNotFoundError,
)
from undine.resolvers import (
    CreateResolver,
    CustomResolver,
    DeleteResolver,
    FunctionResolver,
    ModelFieldResolver,
    ModelManyRelatedResolver,
    UpdateResolver,
)

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo

    from undine.typing import GQLInfo, Root


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


@pytest.mark.django_db
def test_create_resolver():
    project = ProjectFactory.create(name="Test project")
    request = ServiceRequestFactory.create(details="Test request")

    class TaskCreateMutation(MutationType, model=Task): ...

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "request": request.pk,
        "project": project.pk,
    }

    resolver = CreateResolver(mutation_type=TaskCreateMutation)

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(result, Task)
    assert result.name == "Test task"
    assert result.type == TaskTypeChoices.STORY
    assert result.request == request
    assert result.project == project


@pytest.mark.django_db
def test_create_resolver__input_only_fields():
    project = ProjectFactory.create(name="Test project")
    request = ServiceRequestFactory.create(details="Test request")

    validator_called = False

    class TaskCreateMutation(MutationType, model=Task):
        foo = Input(bool, input_only=True)

        @classmethod
        def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validator_called
            validator_called = True

            if input_data["foo"] is not True:
                msg = "Foo must not be True"
                raise ValueError(msg)

    resolver = CreateResolver(mutation_type=TaskCreateMutation)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "request": request.pk,
        "project": project.pk,
        "foo": True,
    }

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(result, Task)
    assert result.name == "Test task"

    assert validator_called is True


@pytest.mark.django_db
def test_create_resolver__atomic():
    project = ProjectFactory.create(name="Test project")

    class ServiceRequestType(MutationType, model=ServiceRequest): ...

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(ServiceRequestType)

    data = {
        "name": "1" * 300,
        "type": TaskTypeChoices.STORY.value,
        "request": {
            "details": "Test request",
            "submittedAt": "2024-01-01",
        },
        "project": project.pk,
    }

    resolver = CreateResolver(mutation_type=TaskCreateMutation)

    with pytest.raises(ValidationError):
        resolver(root=None, info=MockGQLInfo(), input=data)

    assert ServiceRequest.objects.count() == 0
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_update_resolver():
    task = TaskFactory.create(name="Test task")

    class TaskUpdateMutation(MutationType, model=Task): ...

    data = {
        "pk": task.pk,
        "name": "New task",
    }

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation)

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(result, Task)
    assert result.name == "New task"


@pytest.mark.django_db
def test_update_resolver__instance_not_found():
    class TaskUpdateMutation(MutationType, model=Task): ...

    data = {
        "pk": 1,
        "name": "New task",
    }

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation)

    with pytest.raises(GraphQLModelNotFoundError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_update_resolver__lookup_field_not_found():
    class TaskUpdateMutation(MutationType, model=Task): ...

    data = {
        "name": "New task",
    }

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation)

    with pytest.raises(GraphQLMissingLookupFieldError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_update_resolver__input_only_fields():
    task = TaskFactory.create(name="Test task")

    validator_called = False

    class TaskUpdateMutation(MutationType, model=Task):
        foo = Input(bool, input_only=True)

        @classmethod
        def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validator_called
            validator_called = True

            if input_data["foo"] is not True:
                msg = "Foo must not be True"
                raise ValueError(msg)

    data = {
        "pk": task.pk,
        "name": "New task",
        "foo": True,
    }

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation)

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(result, Task)
    assert result.name == "New task"

    assert validator_called is True


@pytest.mark.django_db
def test_update_resolver__atomic():
    task = TaskFactory.create(name="Test task", request__details="Test request")
    request = task.request

    assert request.details == "Test request"

    class ServiceRequestType(MutationType, model=ServiceRequest): ...

    class TaskUpdateMutation(MutationType, model=Task):
        request = Input(ServiceRequestType)

    data = {
        "pk": task.pk,
        "name": "1" * 300,
        "request": {
            "details": "New request",
            "submittedAt": "2024-01-01",
        },
    }

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation)

    with pytest.raises(ValidationError):
        resolver(root=None, info=MockGQLInfo(), input=data)

    task.refresh_from_db()

    assert task.request == request
    assert ServiceRequest.objects.count() == 1


@pytest.mark.django_db
def test_delete_resolver():
    task = TaskFactory.create(name="Test task")

    class TaskDeleteMutation(MutationType, model=Task): ...

    data = {
        "pk": task.pk,
    }

    resolver = DeleteResolver(mutation_type=TaskDeleteMutation)

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert result == {"success": True}

    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_delete_resolver__instance_not_found():
    class TaskDeleteMutation(MutationType, model=Task): ...

    data = {
        "pk": 1,
    }

    resolver = DeleteResolver(mutation_type=TaskDeleteMutation)

    with pytest.raises(GraphQLModelNotFoundError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_delete_resolver__lookup_field_not_found():
    class TaskDeleteMutation(MutationType, model=Task): ...

    data = {}

    resolver = DeleteResolver(mutation_type=TaskDeleteMutation)

    with pytest.raises(GraphQLMissingLookupFieldError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_delete_resolver__input_only_fields():
    task = TaskFactory.create(name="Test task")

    validator_called = False

    class TaskDeleteMutation(MutationType, model=Task):
        foo = Input(bool, input_only=True)

        @classmethod
        def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validator_called
            validator_called = True

            if input_data["foo"] is not True:
                msg = "Foo must not be True"
                raise ValueError(msg)

    data = {
        "pk": task.pk,
        "foo": True,
    }

    resolver = DeleteResolver(mutation_type=TaskDeleteMutation)

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert result == {"success": True}

    assert Task.objects.count() == 0

    assert validator_called is True


@pytest.mark.django_db
def test_delete_resolver__handle_integrity_errors():
    task = TaskFactory.create(name="Test task")
    TaskResultFactory.create(task=task)

    class TaskDeleteMutation(MutationType, model=Task): ...

    data = {
        "pk": task.pk,
    }

    resolver = DeleteResolver(mutation_type=TaskDeleteMutation)

    with pytest.raises(GraphQLModelConstaintViolationError):
        resolver(root=None, info=MockGQLInfo(), input=data)

    assert Task.objects.count() == 1


@pytest.mark.django_db
def test_custom_resolver():
    task = TaskFactory.create(name="Test task")

    mutator_called = False

    class TaskMutation(MutationType, model=Task):
        @classmethod
        def __mutate__(cls, root: Root, info: GQLInfo, input_data: dict[str, Any]) -> Any:
            nonlocal mutator_called
            mutator_called = True
            return "foo"

    data = {
        "pk": task.pk,
    }

    resolver = CustomResolver(mutation_type=TaskMutation)

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert result == "foo"
    assert mutator_called is True
