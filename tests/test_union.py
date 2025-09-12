from __future__ import annotations

import pytest
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString, GraphQLUnionType

from example_project.app.models import Project, Task
from tests.helpers import mock_gql_info
from undine import Field, QueryType, UnionType
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError


def test_union__str() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    assert str(Commentable) == "union Commentable = TaskType | ProjectType"


def test_union__attributes() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    assert Commentable.__query_types_by_model__ == {Task: TaskType, Project: ProjectType}
    assert Commentable.__schema_name__ == "Commentable"
    assert Commentable.__directives__ == []
    assert Commentable.__extensions__ == {"undine_union_type": Commentable}


def test_union__schema_name() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType], schema_name="CustomName"): ...

    assert Commentable.__schema_name__ == "CustomName"


def test_union__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.UNION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType], directives=directives): ...

    assert Commentable.__directives__ == directives

    assert str(Commentable) == 'union Commentable @value(value: "foo") = TaskType | ProjectType'


def test_union__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class Commentable(UnionType[TaskType, ProjectType], directives=directives): ...


def test_union__directives__decorator() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.UNION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    @ValueDirective(value="foo")
    class Commentable(UnionType[TaskType, ProjectType]): ...

    assert Commentable.__directives__ == [ValueDirective(value="foo")]

    assert str(Commentable) == 'union Commentable @value(value: "foo") = TaskType | ProjectType'


def test_union__union_type() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    union_type = Commentable.__union_type__()

    assert isinstance(union_type, GraphQLUnionType)
    assert union_type.name == "Commentable"


def test_union__resolve_type() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    resolver = Commentable.__resolve_type__

    info = mock_gql_info()
    abs_type = Commentable.__union_type__()

    assert resolver(Task(), info, abs_type) == "TaskType"
    assert resolver(Project(), info, abs_type) == "ProjectType"
