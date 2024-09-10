from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.functions import Coalesce, Length, Now

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
from undine import Field, Filter, ModelGQLFilter, ModelGQLOrdering, ModelGQLType, Ordering

if TYPE_CHECKING:
    from undine.typing import GQLInfo


class ContentTypeNode(ModelGQLType, model=ContentType, exclude=["logentry", "permission"]): ...


class PersonNode(ModelGQLType, model=Person): ...


class CommentNode(ModelGQLType, model=Comment): ...


class ServiceRequestNode(ModelGQLType, model=ServiceRequest): ...


class TeamNode(ModelGQLType, model=Team): ...


class ProjectNode(ModelGQLType, model=Project): ...


class TaskResultNode(ModelGQLType, model=TaskResult): ...


class TaskStepNode(ModelGQLType, model=TaskStep): ...


class AcceptanceCriteriaNode(ModelGQLType, model=AcceptanceCriteria): ...


class ReportNode(ModelGQLType, model=Report, filters=True, ordering=True): ...


class TaskFilter(ModelGQLFilter, model=Task):
    """Filter description."""

    has_project = Filter(models.Q(project__isnull=False))
    assignee_count_lt = Filter(models.Count("assignees"), lookup_expr="lt")

    @Filter
    def in_the_past(self, info: GQLInfo, *, value: bool) -> models.Q:
        """FIlter tasks created in the past."""
        return models.Q(created_at__lt=Now()) if value else models.Q(created_at__gte=Now())


class TaskOrdering(ModelGQLOrdering, model=Task):
    """Ordering description."""

    name = Ordering("name")
    custom = Ordering(models.F("created_at"))
    length = Ordering(Length("name"))


class CustomerDetails(TypedDict):
    name: str
    age: int


class TaskNode(ModelGQLType, model=Task, filters=TaskFilter, ordering=TaskOrdering):
    """Task Node description."""

    assignee_count = Field(Coalesce(models.Count("assignees"), 0))

    @Field
    def customer(self, number: int = 18) -> CustomerDetails:
        return CustomerDetails(name="John", age=number)
