from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.functions import Now

from example_project.app.models import (
    AcceptanceCriteria,
    Comment,
    Person,
    Project,
    Report,
    ServiceRequest,
    Task,
    TaskResult,
    TaskStep,
    Team,
)
from undine import Field, Filter, ModelGQLFilter, ModelGQLOrdering, ModelGQLType, Ordering, create_schema

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo


class ContentTypeNode(ModelGQLType, model=ContentType, exclude=["logentry", "permission"]): ...


class PersonNode(ModelGQLType, model=Person): ...


class CommentNode(ModelGQLType, model=Comment): ...


class ServiceRequestNode(ModelGQLType, model=ServiceRequest): ...


class TeamNode(ModelGQLType, model=Team): ...


class ProjectNode(ModelGQLType, model=Project): ...


class TaskResultNode(ModelGQLType, model=TaskResult): ...


class TaskStepNode(ModelGQLType, model=TaskStep): ...


class AcceptanceCriteriaNode(ModelGQLType, model=AcceptanceCriteria): ...


class ReportNode(ModelGQLType, model=Report): ...


class TaskOrdering(ModelGQLOrdering, model=Task):
    """Ordering description."""

    name = Ordering("name")

    @Ordering
    def custom(self) -> models.F:
        """Custom filter for demo purposes."""
        return models.F("created_at")


class TaskFilter(ModelGQLFilter, model=Task):
    """Filter description."""

    has_project = Filter(models.Q(project__isnull=False))
    assignee_count_lt = Filter(models.Count("assignees"), lookup_expr="lt")

    @Filter
    def in_the_past(self, info: GraphQLResolveInfo, *, value: bool) -> models.Q:
        """FIlter tasks created in the past."""
        return models.Q(created_at__lt=Now()) if value else models.Q(created_at__gte=Now())


class TaskNode(ModelGQLType, model=Task, filters=TaskFilter, ordering=TaskOrdering):
    """Task Node description."""


class Query:
    task = Field(TaskNode)
    tasks = Field(TaskNode, many=True)

    @Field
    def function(self, arg: str | None = None) -> list[str | None]:
        """
        Function docstring.

        :param arg: Argument docstring.
        """
        return [arg]


schema = create_schema(query_class=Query)
