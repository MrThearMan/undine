from __future__ import annotations

from django.contrib.contenttypes.models import ContentType

from tests.example.models import (
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
from undine import Field, Filter, ModelGQLFilters, ModelGQLType, create_schema


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


class TaskFilters(ModelGQLFilters, model=Task):
    pk = Filter(lookup_expr="in")
    type = Filter()


class TaskNode(ModelGQLType, model=Task, filters=TaskFilters): ...


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
