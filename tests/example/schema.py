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
from undine import Field, ModelGQLType, create_schema


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


class TaskNode(ModelGQLType, model=Task): ...


class Query:
    task = Field(TaskNode)
    tasks = Field(TaskNode, many=True)


schema = create_schema(query_class=Query)
