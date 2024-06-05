from __future__ import annotations

import pytest

from example_project.app.models import Project, Task, TaskTypeChoices
from tests.factories import ProjectFactory, ServiceRequestFactory, TaskFactory, TeamFactory
from tests.helpers import MockGQLInfo
from undine import Input, MutationType
from undine.errors.exceptions import (
    GraphQLBulkMutationForwardRelationError,
    GraphQLBulkMutationGenericRelationsError,
    GraphQLBulkMutationManyRelatedError,
    GraphQLBulkMutationRelatedObjectNotFoundError,
    GraphQLBulkMutationReverseRelationError,
)
from undine.resolvers import BulkUpdateResolver


@pytest.mark.django_db
def test_bulk_update_resolver():
    project = ProjectFactory.create()
    request = ServiceRequestFactory.create()
    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.STORY.value)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.BUG_FIX.value, request=None)

    class TaskUpdateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(Task.project)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation)

    data = [
        {
            "pk": task_1.pk,
            "name": "Test task 1",
            "type": TaskTypeChoices.BUG_FIX.value,
            "request": request.pk,
            "project": project.pk,
        },
        {
            "pk": task_2.pk,
            "name": "Test task 2",
            "type": TaskTypeChoices.STORY.value,
            "project": project.pk,
        },
    ]

    results = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(results, list)
    assert len(results) == 2

    assert isinstance(results[0], Task)
    assert results[0].name == "Test task 1"
    assert results[0].type == TaskTypeChoices.BUG_FIX
    assert results[0].request == request
    assert results[0].project == project

    assert isinstance(results[1], Task)
    assert results[1].name == "Test task 2"
    assert results[1].type == TaskTypeChoices.STORY
    assert results[1].request is None
    assert results[1].project == project


@pytest.mark.django_db
def test_bulk_update_resolver__related_object_not_found():
    task = TaskFactory.create(request=None)

    class TaskUpdateMutation(MutationType, model=Task):
        request = Input(Task.request)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation)

    data = [
        {
            "pk": task.pk,
            "request": 1,
        },
    ]

    with pytest.raises(GraphQLBulkMutationRelatedObjectNotFoundError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_update_resolver__reverse_relation__one_to_one():
    task = TaskFactory.create()

    class TaskUpdateMutation(MutationType, model=Task):
        result = Input(Task.result)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation)

    data = [
        {
            "pk": task.pk,
            "result": 1,
        },
    ]

    with pytest.raises(GraphQLBulkMutationReverseRelationError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_update_resolver__reverse_relation__one_to_many():
    task = TaskFactory.create()

    class TaskUpdateMutation(MutationType, model=Task):
        steps = Input(Task.steps)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation)

    data = [
        {
            "pk": task.pk,
            "steps": [1],
        },
    ]

    with pytest.raises(GraphQLBulkMutationReverseRelationError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_update_resolver__many_to_many__forward():
    task = TaskFactory.create()

    class TaskUpdateMutation(MutationType, model=Task):
        assignees = Input(Task.assignees)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation)

    data = [
        {
            "pk": task.pk,
            "assignees": [1],
        },
    ]

    with pytest.raises(GraphQLBulkMutationManyRelatedError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_update_resolver__many_to_many__reverse():
    task = TaskFactory.create()

    class TaskUpdateMutation(MutationType, model=Task):
        reports = Input(Task.reports)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation)

    data = [
        {
            "pk": task.pk,
            "reports": [1],
        },
    ]

    with pytest.raises(GraphQLBulkMutationManyRelatedError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_update_resolver__generic_relation():
    task = TaskFactory.create()

    class TaskUpdateMutation(MutationType, model=Task):
        comments = Input(Task.comments)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation)

    data = [
        {
            "pk": task.pk,
            "comments": [1],
        },
    ]

    with pytest.raises(GraphQLBulkMutationGenericRelationsError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_update_resolver__cannot_create_related_object():
    task = TaskFactory.create()
    team = TeamFactory.create()

    class ProjectUpdateMutation(MutationType, model=Project):
        team = Input(Project.team)

    class TaskUpdateMutation(MutationType, model=Task):
        project = Input(ProjectUpdateMutation)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation)

    data = [
        {
            "pk": task.pk,
            "project": {
                "name": "Test project",
                "team": team.pk,
            },
        },
    ]

    with pytest.raises(GraphQLBulkMutationForwardRelationError):
        resolver(root=None, info=MockGQLInfo(), input=data)
