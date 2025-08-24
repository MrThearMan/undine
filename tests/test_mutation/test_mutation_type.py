from __future__ import annotations

from inspect import cleandoc
from typing import Any

import pytest
from graphql import DirectiveLocation, GraphQLInt, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from tests.helpers import exact, mock_gql_info
from undine import Input, MutationType, QueryType
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError, MissingModelGenericError
from undine.typing import GQLInfo, MutationKind
from undine.utils.graphql.type_registry import GRAPHQL_REGISTRY


def test_mutation_type__str() -> None:
    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

    assert str(TaskCreateMutation) == cleandoc(
        """
        input TaskCreateMutation {
          name: String!
        }
        """
    )


def test_mutation_type__registered() -> None:
    assert "MyCreateMutation" not in GRAPHQL_REGISTRY

    class MyCreateMutation(MutationType[Task]): ...

    assert "MyCreateMutation" not in GRAPHQL_REGISTRY

    input_type = MyCreateMutation.__input_type__()

    assert "MyCreateMutation" in GRAPHQL_REGISTRY
    assert GRAPHQL_REGISTRY["MyCreateMutation"] == input_type


def test_mutation_type__attributes() -> None:
    class MyCreateMutation(MutationType[Task]): ...

    assert MyCreateMutation.__model__ == Task
    assert sorted(MyCreateMutation.__input_map__) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "check_time",
        "comments",
        "contact_email",
        "demo_url",
        "done",
        "due_by",
        "external_uuid",
        "extra_data",
        "image",
        "name",
        "objective",
        "points",
        "progress",
        "project",
        "related_tasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "worked_hours",
    ]
    assert MyCreateMutation.__kind__ == MutationKind.create
    assert MyCreateMutation.__schema_name__ == "MyCreateMutation"
    assert MyCreateMutation.__directives__ == []
    assert MyCreateMutation.__extensions__ == {"undine_mutation_type": MyCreateMutation}
    assert MyCreateMutation.__attribute_docstrings__ == {}


def test_mutation_type__input_type() -> None:
    class MyCreateMutation(MutationType[Task]):
        """Description."""

    input_type = MyCreateMutation.__input_type__()
    assert input_type.name == "MyCreateMutation"
    assert input_type.description == "Description."
    assert input_type.extensions == {"undine_mutation_type": MyCreateMutation}

    assert sorted(input_type.fields) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "checkTime",
        "comments",
        "contactEmail",
        "demoUrl",
        "done",
        "dueBy",
        "externalUuid",
        "extraData",
        "image",
        "name",
        "objective",
        "points",
        "progress",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "workedHours",
    ]
    assert input_type.fields["name"].type == GraphQLNonNull(GraphQLString)


def test_mutation_type__input_type__hidden_input() -> None:
    class MyCreateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()
        foo = Input(str, hidden=True)

    input_type = MyCreateMutation.__input_type__()

    assert sorted(input_type.fields) == ["name", "pk"]
    assert "foo" in MyCreateMutation.__input_map__


def test_mutation_type__output_type() -> None:
    class MyQueryType(QueryType[Task]): ...

    class MyCreateMutation(MutationType[Task]): ...

    assert MyCreateMutation.__output_type__() == MyQueryType.__output_type__()


def test_mutation_type__no_model() -> None:
    with pytest.raises(MissingModelGenericError):

        class MyCreateMutation(MutationType): ...


def test_mutation_type__kind__create__implicit() -> None:
    class MyCreateMutation(MutationType[Task]): ...

    assert MyCreateMutation.__kind__ == MutationKind.create


def test_mutation_type__kind__create__explicit() -> None:
    class TaskCreateMutation(MutationType[Task], kind="create"): ...

    assert TaskCreateMutation.__kind__ == MutationKind.create


def test_mutation_type__kind__create__primary_key() -> None:
    class MyCreateMutation(MutationType[Task]): ...

    assert "pk" not in MyCreateMutation.__input_map__


def test_mutation_type__kind__create__output_type() -> None:
    class MyQueryType(QueryType[Task]): ...

    class MyCreateMutation(MutationType[Task]): ...

    assert MyCreateMutation.__output_type__() == MyQueryType.__output_type__()


def test_mutation_type__kind__update__implicit() -> None:
    class TaskUpdateMutation(MutationType[Task]): ...

    assert TaskUpdateMutation.__kind__ == MutationKind.update


def test_mutation_type__kind__update__explicit() -> None:
    class TaskCreateMutation(MutationType[Task], kind="update"): ...

    assert TaskCreateMutation.__kind__ == MutationKind.update


def test_mutation_type__kind__update__primary_key() -> None:
    class TaskUpdateMutation(MutationType[Task]): ...

    assert "pk" in TaskUpdateMutation.__input_map__


def test_mutation_type__kind__update__output_type() -> None:
    class MyQueryType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    assert TaskUpdateMutation.__output_type__() == MyQueryType.__output_type__()


def test_mutation_type__kind__delete__implicit() -> None:
    class MyDeleteMutation(MutationType[Task]): ...

    assert MyDeleteMutation.__kind__ == MutationKind.delete


def test_mutation_type__kind__delete__explicit() -> None:
    class TaskCreateMutation(MutationType[Task], kind="delete"): ...

    assert TaskCreateMutation.__kind__ == MutationKind.delete


def test_mutation_type__kind__delete__primary_key() -> None:
    class MyDeleteMutation(MutationType[Task]): ...

    assert "pk" in MyDeleteMutation.__input_map__


def test_mutation_type__kind__delete__output_type() -> None:
    class TaskType(QueryType[Task]): ...

    class MyDeleteMutation(MutationType[Task]): ...

    output_type = MyDeleteMutation.__output_type__()
    assert output_type.name == "MyDeleteMutationOutput"
    assert sorted(output_type.fields) == ["pk"]
    assert output_type.fields["pk"].type == GraphQLNonNull(GraphQLInt)
    assert output_type.fields["pk"].description is None
    assert output_type.fields["pk"].deprecation_reason is None


def test_mutation_type__kind__custom__single() -> None:
    class MyOtherMutation(MutationType[Task]):
        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Any:
            return instance

    assert MyOtherMutation.__kind__ == MutationKind.custom


def test_mutation_type__kind__custom__many() -> None:
    class MyOtherMutation(MutationType[Task]):
        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: list[dict[str, Any]]) -> Any:
            return instances

    assert MyOtherMutation.__kind__ == MutationKind.custom


def test_mutation_type__kind__related() -> None:
    class MyRelatedMutation(MutationType[Task], kind="related"): ...

    assert MyRelatedMutation.__kind__ == MutationKind.related
    assert "pk" in MyRelatedMutation.__input_map__


def test_mutation_type__kind__related__output_type() -> None:
    class MyQueryType(QueryType[Task]): ...

    class MyRelatedMutation(MutationType[Task], kind="related"): ...

    assert MyRelatedMutation.__output_type__() == MyQueryType.__output_type__()


def test_mutation_type__auto__false() -> None:
    class MyCreateMutation(MutationType[Task], auto=False): ...

    assert MyCreateMutation.__input_map__ == {}


def test_mutation_type__exclude() -> None:
    class TaskUpdateMutation(MutationType[Task], exclude=["name"]): ...

    assert sorted(TaskUpdateMutation.__input_map__) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "check_time",
        "comments",
        "contact_email",
        "demo_url",
        "done",
        "due_by",
        "external_uuid",
        "extra_data",
        "image",
        "objective",
        "pk",
        "points",
        "progress",
        "project",
        "related_tasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "worked_hours",
    ]

    input_type = TaskUpdateMutation.__input_type__()
    assert sorted(input_type.fields) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "checkTime",
        "comments",
        "contactEmail",
        "demoUrl",
        "done",
        "dueBy",
        "externalUuid",
        "extraData",
        "image",
        "objective",
        "pk",
        "points",
        "progress",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "workedHours",
    ]


def test_mutation_type__exclude__multiple() -> None:
    class TaskUpdateMutation(MutationType[Task], exclude=["name", "done"]): ...

    assert sorted(TaskUpdateMutation.__input_map__) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "check_time",
        "comments",
        "contact_email",
        "demo_url",
        "due_by",
        "external_uuid",
        "extra_data",
        "image",
        "objective",
        "pk",
        "points",
        "progress",
        "project",
        "related_tasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "worked_hours",
    ]

    input_type = TaskUpdateMutation.__input_type__()
    assert sorted(input_type.fields) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "checkTime",
        "comments",
        "contactEmail",
        "demoUrl",
        "dueBy",
        "externalUuid",
        "extraData",
        "image",
        "objective",
        "pk",
        "points",
        "progress",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "workedHours",
    ]


def test_mutation_type__schema_name() -> None:
    class TaskCreateMutation(MutationType[Task], schema_name="CustomName"): ...

    assert TaskCreateMutation.__schema_name__ == "CustomName"

    input_type = TaskCreateMutation.__input_type__()
    assert input_type.name == "CustomName"


def test_mutation_type__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class TaskCreateMutation(MutationType[Task], directives=directives, auto=False):
        name = Input()

    assert TaskCreateMutation.__directives__ == directives

    assert str(TaskCreateMutation) == cleandoc(
        """
        input TaskCreateMutation @value(value: "foo") {
          name: String!
        }
        """
    )


def test_mutation_type__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class TaskCreateMutation(MutationType[Task], directives=directives): ...


def test_mutation_type__extensions() -> None:
    class TaskCreateMutation(MutationType[Task], extensions={"foo": "bar"}): ...

    assert TaskCreateMutation.__extensions__ == {"foo": "bar", "undine_mutation_type": TaskCreateMutation}

    input_type = TaskCreateMutation.__input_type__()
    assert input_type.extensions == {"foo": "bar", "undine_mutation_type": TaskCreateMutation}


def test_mutation_type__validate() -> None:
    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            if input_data["foo"] is not True:
                msg = "Foo must be True"
                raise ValueError(msg)

    TaskCreateMutation.__validate__(Task(), mock_gql_info(), {"foo": True})

    with pytest.raises(ValueError, match=exact("Foo must be True")):
        TaskCreateMutation.__validate__(Task(), mock_gql_info(), {"foo": False})
