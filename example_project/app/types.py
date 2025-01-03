from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, F, Q
from django.db.models.functions import Coalesce, Length, Now, Upper

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
from undine.relay import Connection, Node

if TYPE_CHECKING:
    from undine.typing import GQLInfo


class ContentTypeType(QueryType, model=ContentType, exclude=["logentry", "permission"]): ...


class PersonType(QueryType, model=Person, filterset=True, orderset=True, interfaces=[Node]): ...


class CommentType(QueryType, model=Comment, filterset=True, orderset=True): ...


class ServiceRequestType(QueryType, model=ServiceRequest, filterset=True, orderset=True): ...


class TeamType(QueryType, model=Team, filterset=True, orderset=True): ...


class ProjectType(QueryType, model=Project, filterset=True, orderset=True): ...


class TaskResultType(QueryType, model=TaskResult, filterset=True, orderset=True): ...


class TaskObjectiveType(QueryType, model=TaskObjective, filterset=True, orderset=True): ...


class TaskStepType(QueryType, model=TaskStep, filterset=True, orderset=True): ...


class AcceptanceCriteriaType(QueryType, model=AcceptanceCriteria, filterset=True, orderset=True): ...


class ReportType(QueryType, model=Report, filterset=True, orderset=True): ...


class TaskFilterSet(FilterSet, model=Task):
    """Filter description."""

    has_project = Filter(Q(project__isnull=False))
    assignee_count_lt = Filter(Count("assignees"), lookup="lt")

    @Filter
    def in_the_past(self, info: GQLInfo, *, value: bool) -> Q:
        """Filter tasks created in the past."""
        return Q(created_at__lt=Now()) if value else Q(created_at__gte=Now())


class TaskOrderSet(OrderSet, model=Task):
    """Order description."""

    name = Order("name")
    custom = Order(F("created_at"))
    length = Order(Length("name"))


class CustomerDetails(TypedDict):
    name: str
    age: int


class TaskType(QueryType, model=Task, filterset=TaskFilterSet, orderset=TaskOrderSet, interfaces=[Node]):
    """Task Node description."""

    name = Field()

    name_upper = Field(Upper("name"))

    assignees = Field(Connection(PersonType))

    @name.permissions
    def name_permissions(self, info: GQLInfo, instance: Task) -> None:
        return

    assignee_count = Field(Coalesce(Count("assignees"), 0))

    @Field
    def customer(self, number: int = 18) -> CustomerDetails:
        return CustomerDetails(name="John", age=number)
