from __future__ import annotations

import pytest

from example_project.app.models import Project, Task, TaskTypeChoices
from tests.factories import (
    PersonFactory,
    ProjectFactory,
    ReportFactory,
    ServiceRequestFactory,
    TaskResultFactory,
    TaskStepFactory,
    TeamFactory,
)
from tests.helpers import MockGQLInfo
from undine import Input, MutationType
from undine.errors.exceptions import (
    GraphQLBulkMutationForwardRelationError,
    GraphQLBulkMutationGenericRelationsError,
    GraphQLBulkMutationManyRelatedError,
    GraphQLBulkMutationRelatedObjectNotFoundError,
    GraphQLBulkMutationReverseRelationError,
)
from undine.resolvers import BulkCreateResolver


@pytest.mark.django_db
def test_bulk_create_resolver():
    project = ProjectFactory.create()
    request = ServiceRequestFactory.create()

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(Task.project)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation)

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
            "request": request.pk,
            "project": project.pk,
        },
        {
            "name": "Test task 2",
            "type": TaskTypeChoices.BUG_FIX.value,
            "project": project.pk,
        },
    ]

    results = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(results, list)
    assert len(results) == 2

    assert isinstance(results[0], Task)
    assert results[0].name == "Test task 1"
    assert results[0].type == TaskTypeChoices.STORY
    assert results[0].request == request
    assert results[0].project == project

    assert isinstance(results[1], Task)
    assert results[1].name == "Test task 2"
    assert results[1].type == TaskTypeChoices.BUG_FIX
    assert results[1].request is None
    assert results[1].project == project


@pytest.mark.django_db
def test_bulk_create_resolver__related_object_not_found():
    request = ServiceRequestFactory.create()

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(Task.project)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": request.pk,
            "project": 1,
        },
    ]

    with pytest.raises(GraphQLBulkMutationRelatedObjectNotFoundError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_create_resolver__reverse_relation__one_to_one():
    project = ProjectFactory.create()
    request = ServiceRequestFactory.create()
    result = TaskResultFactory.create()

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(Task.project)
        result = Input(Task.result)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": request.pk,
            "project": project.pk,
            "result": result.pk,
        },
    ]

    with pytest.raises(GraphQLBulkMutationReverseRelationError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_create_resolver__reverse_relation__one_to_many():
    project = ProjectFactory.create()
    request = ServiceRequestFactory.create()
    step = TaskStepFactory.create()

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(Task.project)
        steps = Input(Task.steps)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": request.pk,
            "project": project.pk,
            "steps": [step.pk],
        },
    ]

    with pytest.raises(GraphQLBulkMutationReverseRelationError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_create_resolver__many_to_many__forward():
    project = ProjectFactory.create()
    request = ServiceRequestFactory.create()
    assignee = PersonFactory.create()

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(Task.project)
        assignees = Input(Task.assignees)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": request.pk,
            "project": project.pk,
            "assignees": [assignee.pk],
        },
    ]

    with pytest.raises(GraphQLBulkMutationManyRelatedError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_create_resolver__many_to_many__reverse():
    project = ProjectFactory.create()
    request = ServiceRequestFactory.create()
    report = ReportFactory.create()

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(Task.project)
        reports = Input(Task.reports)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": request.pk,
            "project": project.pk,
            "reports": [report.pk],
        },
    ]

    with pytest.raises(GraphQLBulkMutationManyRelatedError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_create_resolver__generic_relation():
    project = ProjectFactory.create()
    request = ServiceRequestFactory.create()
    comment = PersonFactory.create()

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(Task.project)
        comments = Input(Task.comments)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": request.pk,
            "project": project.pk,
            "comments": [comment.pk],
        },
    ]

    with pytest.raises(GraphQLBulkMutationGenericRelationsError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_bulk_create_resolver__cannot_create_related_object():
    request = ServiceRequestFactory.create()
    team = TeamFactory.create()

    class ProjectCreateMutation(MutationType, model=Project):
        team = Input(Project.team)

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(ProjectCreateMutation)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation)

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": request.pk,
            "project": {
                "name": "Test project",
                "team": team.pk,
            },
        },
    ]

    with pytest.raises(GraphQLBulkMutationForwardRelationError):
        resolver(root=None, info=MockGQLInfo(), input=data)
