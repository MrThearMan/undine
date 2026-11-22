from __future__ import annotations

from typing import Any

import pytest

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory, TeamFactory
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.utils import pre_mutation as pm

SEEN: list[Any] = []


def build_schema(undine_settings) -> None:
    class TaskType(QueryType[Task]): ...

    class RelatedProject(MutationType[Project], kind="related"):
        pk = Input()
        name = Input()

        @classmethod
        def __permissions__(cls, instance: Project, info: GQLInfo, input_data: dict[str, Any]) -> None:
            SEEN.append((instance.pk, instance.name, instance.team_id))

    class TaskUpdateMutation(MutationType[Task]):
        pk = Input()
        project = Input(RelatedProject)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)


@pytest.mark.parametrize("full_clean", [True, False])
@pytest.mark.parametrize("n", [2, 10])
@pytest.mark.django_db
def test_poc(graphql, undine_settings, n, full_clean):
    undine_settings.MUTATION_FULL_CLEAN = full_clean
    SEEN.clear()
    build_schema(undine_settings)
    team = TeamFactory.create()
    tasks = [TaskFactory.create(project=ProjectFactory.create(name=f"old {i}", team=team)) for i in range(n)]
    data = [{"pk": t.pk, "project": {"pk": t.project.pk, "name": f"new {i}"}} for i, t in enumerate(tasks)]
    query = "mutation($input: [TaskUpdateMutation!]!) { bulkUpdateTask(input: $input) { pk } }"

    response = graphql(query, variables={"input": data}, count_queries=True)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_poc_missing_pk(graphql, undine_settings):
    SEEN.clear()
    build_schema(undine_settings)
    task = TaskFactory.create(project=ProjectFactory.create(name="old"))
    data = [{"pk": task.pk, "project": {"pk": 999, "name": "x"}}]
    query = "mutation($input: [TaskUpdateMutation!]!) { bulkUpdateTask(input: $input) { pk } }"
    graphql(query, variables={"input": data})


@pytest.mark.django_db
def test_poc_same_pk_twice(graphql, undine_settings):
    SEEN.clear()
    build_schema(undine_settings)
    project = ProjectFactory.create(name="old")
    t1 = TaskFactory.create(project=project)
    t2 = TaskFactory.create(project=project)
    data = [
        {"pk": t1.pk, "project": {"pk": project.pk, "name": "a"}},
        {"pk": t2.pk, "project": {"pk": project.pk, "name": "b"}},
    ]
    query = "mutation($input: [TaskUpdateMutation!]!) { bulkUpdateTask(input: $input) { pk } }"
    graphql(query, variables={"input": data}, count_queries=True)


@pytest.mark.django_db
def test_poc_identity(graphql, undine_settings):
    """Does the check see the same object that mutate() saves?"""
    SEEN.clear()
    build_schema(undine_settings)

    captured = []
    original = pm._permissions

    def spy(**kwargs):
        captured.append((kwargs["mutation_type"].__name__, id(kwargs["instance"])))
        return original(**kwargs)

    pm._permissions = spy
    try:
        project = ProjectFactory.create(name="old")
        t1 = TaskFactory.create(project=project)
        data = [{"pk": t1.pk, "project": {"pk": project.pk, "name": "a"}}]
        query = "mutation($input: [TaskUpdateMutation!]!) { bulkUpdateTask(input: $input) { pk } }"
        response = graphql(query, variables={"input": data})
        assert response.has_errors is False
    finally:
        pm._permissions = original
