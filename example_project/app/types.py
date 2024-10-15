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
    TaskObjective,
    TaskResult,
    TaskStep,
    Team,
)
from undine import Field, Filter, Order
from undine.filtering import FilterSet
from undine.ordering import OrderSet
from undine.query import QueryType

if TYPE_CHECKING:
    from undine.typing import GQLInfo


class ContentTypeType(QueryType, model=ContentType, exclude=["logentry", "permission"]): ...


class PersonType(QueryType, model=Person): ...


class CommentType(QueryType, model=Comment): ...


class ServiceRequestType(QueryType, model=ServiceRequest): ...


class TeamType(QueryType, model=Team): ...


class ProjectType(QueryType, model=Project): ...


class TaskResultType(QueryType, model=TaskResult): ...


class TaskObjectiveType(QueryType, model=TaskObjective): ...


class TaskStepType(QueryType, model=TaskStep): ...


class AcceptanceCriteriaType(QueryType, model=AcceptanceCriteria): ...


class ReportType(QueryType, model=Report, filterset=True, orderset=True): ...


class TaskFilterSet(FilterSet, model=Task):
    """Filter description."""

    has_project = Filter(models.Q(project__isnull=False))
    assignee_count_lt = Filter(models.Count("assignees"), lookup_expr="lt")

    @Filter
    def in_the_past(self, info: GQLInfo, *, value: bool) -> models.Q:
        """Filter tasks created in the past."""
        return models.Q(created_at__lt=Now()) if value else models.Q(created_at__gte=Now())


class TaskOrderSet(OrderSet, model=Task):
    """Order description."""

    name = Order("name")
    custom = Order(models.F("created_at"))
    length = Order(Length("name"))


class CustomerDetails(TypedDict):
    name: str
    age: int


class TaskType(QueryType, model=Task, filterset=TaskFilterSet, orderset=TaskOrderSet):
    """Task Node description."""

    assignee_count = Field(Coalesce(models.Count("assignees"), 0))

    @Field
    def customer(self, number: int = 18) -> CustomerDetails:
        return CustomerDetails(name="John", age=number)
