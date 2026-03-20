from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable
from typing import TypedDict

from django.db.models import Count, F, Q, Value
from django.db.models.functions import Coalesce, Length, Now, Upper
from graphql import DirectiveLocation, GraphQLError, GraphQLNonNull, GraphQLString

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
from undine import (
    Calculation,
    CalculationArgument,
    Field,
    Filter,
    FilterSet,
    InterfaceField,
    InterfaceType,
    Order,
    OrderSet,
    QueryType,
    UnionType,
)
from undine.directives import ComplexityDirective, Directive, DirectiveArgument
from undine.optimizer import OptimizationData
from undine.relay import Connection, Node
from undine.typing import DjangoExpression, DjangoRequestProtocol, GQLInfo


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


@Node
@Named
class PersonType(QueryType[Person]): ...


class CommentType(QueryType[Comment], exclude=["content_type"]): ...


class ServiceRequestType(QueryType[ServiceRequest]): ...


@Named
class TeamType(QueryType[Team]): ...


class ProjectFilterSet(FilterSet[Project]): ...


@Named
@ProjectFilterSet
class ProjectType(QueryType[Project]): ...


class TaskResultType(QueryType[TaskResult]): ...


class TaskObjectiveType(QueryType[TaskObjective]): ...


@Named
class TaskStepType(QueryType[TaskStep]): ...


class AcceptanceCriteriaType(QueryType[AcceptanceCriteria]): ...


@Named
class ReportType(QueryType[Report]): ...


class TaskFilterSet(FilterSet[Task]):
    """Filter description."""

    has_project = Filter(Q(project__isnull=False))
    assignee_count_lt = Filter(Count("assignees"), lookup="lt")

    @Filter
    def in_the_past(self, info: GQLInfo, *, value: bool) -> Q:
        """Filter tasks created in the past."""
        return Q(created_at__lt=Now()) if value else Q(created_at__gte=Now())

    @has_project.visible
    def has_project_visible(self, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser


class TaskOrderSet(OrderSet[Task]):
    """Order description."""

    name = Order("name")
    custom = Order(F("created_at"))
    length = Order(Length("name"))


class CustomerDetails(TypedDict):
    name: str
    age: int


class MyDirective(Directive, locations=[DirectiveLocation.FIELD]):
    """My custom directive."""

    name = DirectiveArgument(GraphQLString)


class ExampleCalculation(Calculation[int]):
    value = CalculationArgument(int)

    def __call__(self, info: GQLInfo) -> DjangoExpression:
        return Value(self.value)


@Node
@Named
@TaskFilterSet
@TaskOrderSet
class TaskType(QueryType[Task]):
    """Task Node description."""

    name = Field() @ ComplexityDirective(value=1)

    name_upper = Field(Upper("name"), complexity=1)

    assignees = Field(Connection(PersonType))

    @name.permissions
    def name_permissions(self, info: GQLInfo, instance: Task) -> None:
        return

    assignee_count = Field(Coalesce(Count("assignees"), 0))

    @Field
    def customer(self, number: int = 18) -> CustomerDetails:
        return CustomerDetails(name="John", age=number)

    example = Field(ExampleCalculation)

    @Field
    async def slow(self: Task, info: GQLInfo) -> int:
        sleep_time = (self.points or 0) % 10
        await asyncio.sleep(sleep_time)
        return sleep_time

    @slow.optimize
    def slow_optimized(self, data: OptimizationData, info: GQLInfo) -> None:
        return data.only_fields.add("points")

    @Field
    async def echo(self: Task, info: GQLInfo) -> AsyncIterable[str]:
        iterations = (self.points or 0) % 10
        for _ in range(iterations):
            await asyncio.sleep(1)
            yield "echo"

    @echo.optimize
    def echo_optimized(self, data: OptimizationData, info: GQLInfo) -> None:
        return data.only_fields.add("points")

    @Field(errors=[GraphQLError])
    def points(self: Task, info: GQLInfo) -> int:
        if self.points is None:
            msg = "No points set for this task"
            raise GraphQLError(msg)
        return self.points


class CommentableFilterSet(FilterSet[Task, Project, Report], auto=True): ...


class CommentableOrderSet(OrderSet[Task, Project, Report], auto=True): ...


@CommentableFilterSet
@CommentableOrderSet
class Commentable(UnionType[TaskType, ProjectType, ReportType]):
    """All entities that can be commented on"""
