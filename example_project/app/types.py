from __future__ import annotations

from typing import TypedDict

from django.db.models import Count, F, Q
from django.db.models.functions import Coalesce, Length, Now, Upper
from graphql import GraphQLNonNull, GraphQLString

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
from undine import Field, Filter, InterfaceField, InterfaceType, Order, UnionType
from undine.filtering import FilterSet
from undine.ordering import OrderSet
from undine.query import QueryType
from undine.relay import Connection, Node
from undine.typing import GQLInfo


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


class PersonType(QueryType[Person], interfaces=[Node, Named]): ...


class CommentType(QueryType[Comment], exclude=["content_type"]): ...


class ServiceRequestType(QueryType[ServiceRequest]): ...


class TeamType(QueryType[Team], interfaces=[Named]): ...


class ProjectFilterSet(FilterSet[Project]): ...


class ProjectType(QueryType[Project], filterset=ProjectFilterSet, interfaces=[Named]): ...


class TaskResultType(QueryType[TaskResult]): ...


class TaskObjectiveType(QueryType[TaskObjective]): ...


class TaskStepType(QueryType[TaskStep], interfaces=[Named]): ...


class AcceptanceCriteriaType(QueryType[AcceptanceCriteria]): ...


class ReportType(QueryType[Report], interfaces=[Named]): ...


class TaskFilterSet(FilterSet[Task]):
    """Filter description."""

    has_project = Filter(Q(project__isnull=False))
    assignee_count_lt = Filter(Count("assignees"), lookup="lt")

    @Filter
    def in_the_past(self, info: GQLInfo, *, value: bool) -> Q:
        """Filter tasks created in the past."""
        return Q(created_at__lt=Now()) if value else Q(created_at__gte=Now())


class TaskOrderSet(OrderSet[Task]):
    """Order description."""

    name = Order("name")
    custom = Order(F("created_at"))
    length = Order(Length("name"))


class CustomerDetails(TypedDict):
    name: str
    age: int


class TaskType(QueryType[Task], filterset=TaskFilterSet, orderset=TaskOrderSet, interfaces=[Node, Named]):
    """Task Node description."""

    name = Field()

    name_upper = Field(Upper("name"), complexity=1)

    assignees = Field(Connection(PersonType))

    @name.permissions
    def name_permissions(self, info: GQLInfo, instance: Task) -> None:
        return

    assignee_count = Field(Coalesce(Count("assignees"), 0))

    @Field
    def customer(self, number: int = 18) -> CustomerDetails:
        return CustomerDetails(name="John", age=number)


class Commentable(UnionType[TaskType, ProjectType]): ...
