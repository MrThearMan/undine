from __future__ import annotations

from graphql import GraphQLInt, GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task
from undine import Field, InterfaceField, InterfaceType, QueryType
from undine.converters import convert_to_field_complexity
from undine.utils.model_utils import get_model_field


def test_convert_to_field_complexity__field() -> None:
    field = get_model_field(model=Task, lookup="name")

    class TaskType(QueryType[Task]):
        name = Field(field)

    result = convert_to_field_complexity(field, caller=TaskType.name)
    assert result == 0


def test_convert_to_field_complexity__field__relation() -> None:
    field = get_model_field(model=Task, lookup="request")

    class TaskType(QueryType[Task]):
        request = Field(field)

    result = convert_to_field_complexity(field, caller=TaskType.request)
    assert result == 1


def test_convert_to_field_complexity__query_type() -> None:
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    result = convert_to_field_complexity(ProjectType, caller=TaskType.project)
    assert result == 1


def test_convert_to_field_complexity__interface_field() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    @Named
    class TaskType(QueryType[Task]):
        name = Field()

    result = convert_to_field_complexity(Named.name, caller=TaskType.name)
    assert result == 0


def test_convert_to_field_complexity__interface_field__related() -> None:
    class InProject(InterfaceType):
        project = InterfaceField(GraphQLInt)

    @InProject
    class TaskType(QueryType[Task]):
        project = Field()

    result = convert_to_field_complexity(InProject.project, caller=TaskType.project)
    assert result == 1
