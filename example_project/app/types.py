from __future__ import annotations

from typing import TypedDict

from django.db.models import Count, F, Q, Value
from django.db.models.functions import Coalesce, Length, Now, Upper
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

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
from undine.directives import Directive, DirectiveArgument
from undine.relay import Connection, Node
from undine.typing import DjangoExpression, DjangoRequestProtocol, GQLInfo


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))

    # @name.visible
    # def name_visible(self, request: DjangoRequestProtocol) -> bool:
    #     return request.user.is_superuser


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

    @has_project.visible
    def has_project_visible(self, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser

    # @classmethod
    # def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
    #     return request.user.is_superuser


class TaskOrderSet(OrderSet[Task]):
    """Order description."""

    name = Order("name")
    custom = Order(F("created_at"))
    length = Order(Length("name"))

    # @name.visible
    # def name_visible(self, request: DjangoRequestProtocol) -> bool:
    #     return request.user.is_superuser


class CustomerDetails(TypedDict):
    name: str
    age: int


class MyDirective(Directive, locations=[DirectiveLocation.FIELD]):
    """My custom directive."""

    name = DirectiveArgument(GraphQLString)

    # @name.visible
    # def name_visible(self, request: DjangoRequestProtocol) -> bool:
    #     return request.user.is_superuser


class ExampleCalculation(Calculation[int]):
    value = CalculationArgument(int)

    # @value.visible
    # def value_visible(self, request: DjangoRequestProtocol) -> bool:
    #     return request.user.is_superuser

    def __call__(self, info: GQLInfo) -> DjangoExpression:
        return Value(self.value)


class TaskType(QueryType[Task], filterset=TaskFilterSet, orderset=TaskOrderSet, interfaces=[Node, Named]):
    """Task Node description."""

    name = Field()

    name_upper = Field(Upper("name"), complexity=1)

    assignees = Field(Connection(PersonType))

    @name.permissions
    def name_permissions(self, info: GQLInfo, instance: Task) -> None:
        return

    assignee_count = Field(Coalesce(Count("assignees"), 0))

    # @assignee_count.visible
    # def assignees_count_visible(self, request: DjangoRequestProtocol) -> bool:
    #     return request.user.is_superuser

    @Field
    def customer(self, number: int = 18) -> CustomerDetails:
        return CustomerDetails(name="John", age=number)

    example = Field(ExampleCalculation)

    # @classmethod
    # def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
    #     return request.user.is_superuser


class Commentable(UnionType[TaskType, ProjectType]):
    """All entities that can be commented on"""

    # @classmethod
    # def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
    #     return request.user.is_superuser
