from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator

import pytest
from graphql import GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from tests.helpers import MockGQLInfo, exact
from undine import MutationType, QueryType
from undine.errors.exceptions import MissingModelError
from undine.mutation import DeleteMutationOutputType
from undine.registies import GRAPHQL_TYPE_REGISTRY

if TYPE_CHECKING:
    from undine.typing import GQLInfo, MutationMiddlewareParams, MutationMiddlewareType, Root


def test_mutation_type__registered():
    assert "MyCreateMutation" not in GRAPHQL_TYPE_REGISTRY

    class MyCreateMutation(MutationType, model=Task): ...

    assert "MyCreateMutation" not in GRAPHQL_TYPE_REGISTRY

    input_type = MyCreateMutation.__input_type__()

    assert "MyCreateMutation" in GRAPHQL_TYPE_REGISTRY
    assert GRAPHQL_TYPE_REGISTRY["MyCreateMutation"] == input_type


def test_mutation_type__attributes():
    class MyCreateMutation(MutationType, model=Task): ...

    assert MyCreateMutation.__model__ == Task
    assert MyCreateMutation.__lookup_field__ == "pk"
    assert MyCreateMutation.__mutation_kind__ == "create"
    assert MyCreateMutation.__typename__ == "MyCreateMutation"
    assert MyCreateMutation.__extensions__ == {"undine_mutation": MyCreateMutation}
    assert sorted(MyCreateMutation.__input_map__) == [
        "acceptancecriteria",
        "assignees",
        "comments",
        "name",
        "objective",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
    ]


def test_mutation_type__middleware():
    def my_middleware(params: MutationMiddlewareParams) -> Generator:
        yield

    class MyCreateMutation(MutationType, model=Task):
        @classmethod
        def __middleware__(cls) -> list[MutationMiddlewareType]:
            return [my_middleware]

    assert MyCreateMutation.__middleware__() == [my_middleware]


def test_mutation_type__input_type():
    class MyCreateMutation(MutationType, model=Task):
        """Description."""

    input_type = MyCreateMutation.__input_type__()
    assert input_type.name == "MyCreateMutation"
    assert input_type.description == "Description."
    assert input_type.extensions == {"undine_mutation": MyCreateMutation}

    assert sorted(input_type.fields) == [
        "acceptancecriteria",
        "assignees",
        "comments",
        "name",
        "objective",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
    ]
    assert input_type.fields["name"].type == GraphQLNonNull(GraphQLString)


def test_mutation_type__output_type():
    class MyQueryType(QueryType, model=Task): ...

    class MyCreateMutation(MutationType, model=Task): ...

    assert MyCreateMutation.__output_type__() == MyQueryType.__output_type__()


def test_mutation_type__no_model():
    with pytest.raises(MissingModelError):

        class MyCreateMutation(MutationType): ...


def test_mutation_type__mutation_kind__create__implicit():
    class MyCreateMutation(MutationType, model=Task): ...

    assert MyCreateMutation.__mutation_kind__ == "create"


def test_mutation_type__mutation_kind__create__explicit():
    class MyMutation(MutationType, model=Task, mutation_kind="create"): ...

    assert MyMutation.__mutation_kind__ == "create"


def test_mutation_type__mutation_kind__create__primary_key():
    class MyCreateMutation(MutationType, model=Task): ...

    assert MyCreateMutation.__lookup_field__ not in MyCreateMutation.__input_map__


def test_mutation_type__mutation_kind__create__output_type():
    class MyQueryType(QueryType, model=Task): ...

    class MyCreateMutation(MutationType, model=Task): ...

    assert MyCreateMutation.__output_type__() == MyQueryType.__output_type__()


def test_mutation_type__mutation_kind__update__implicit():
    class MyUpdateMutation(MutationType, model=Task): ...

    assert MyUpdateMutation.__mutation_kind__ == "update"


def test_mutation_type__mutation_kind__update__explicit():
    class MyMutation(MutationType, model=Task, mutation_kind="update"): ...

    assert MyMutation.__mutation_kind__ == "update"


def test_mutation_type__mutation_kind__update__primary_key():
    class MyUpdateMutation(MutationType, model=Task): ...

    assert MyUpdateMutation.__lookup_field__ in MyUpdateMutation.__input_map__


def test_mutation_type__mutation_kind__update__output_type():
    class MyQueryType(QueryType, model=Task): ...

    class MyUpdateMutation(MutationType, model=Task): ...

    assert MyUpdateMutation.__output_type__() == MyQueryType.__output_type__()


def test_mutation_type__mutation_kind__delete__implicit():
    class MyDeleteMutation(MutationType, model=Task): ...

    assert MyDeleteMutation.__mutation_kind__ == "delete"


def test_mutation_type__mutation_kind__delete__exlicit():
    class MyMutation(MutationType, model=Task, mutation_kind="delete"): ...

    assert MyMutation.__mutation_kind__ == "delete"


def test_mutation_type__mutation_kind__delete__primary_key():
    class MyDeleteMutation(MutationType, model=Task): ...

    assert MyDeleteMutation.__lookup_field__ in MyDeleteMutation.__input_map__


def test_mutation_type__mutation_kind__delete__output_type():
    class MyDeleteMutation(MutationType, model=Task): ...

    assert MyDeleteMutation.__output_type__() == DeleteMutationOutputType


def test_mutation_type__mutation_kind__custom__implicit():
    class MyOtherMutation(MutationType, model=Task): ...

    assert MyOtherMutation.__mutation_kind__ == "custom"


def test_mutation_type__mutation_kind__custom__implicit__from_method_defined():
    class MyCreateMutation(MutationType, model=Task):
        def __mutate__(self, root: Root, info: GQLInfo, input_data: dict[str, Any]) -> Any: ...

    assert MyCreateMutation.__mutation_kind__ == "custom"


def test_mutation_type__mutation_kind__custom__explicit():
    class MyCreateMutation(MutationType, model=Task, mutation_kind="custom"): ...

    assert MyCreateMutation.__mutation_kind__ == "custom"


def test_mutation_type__mutation_kind__custom__primary_key():
    class MyOtherMutation(MutationType, model=Task): ...

    assert MyOtherMutation.__lookup_field__ in MyOtherMutation.__input_map__


def test_mutation_type__mutation_kind__custom__output_type():
    class MyQueryType(QueryType, model=Task): ...

    class MyOtherMutation(MutationType, model=Task): ...

    assert MyOtherMutation.__output_type__() == MyQueryType.__output_type__()


def test_mutation_type__auto():
    class MyMutation(MutationType, model=Task, auto=False): ...

    assert MyMutation.__input_map__ == {}


def test_mutation_type__exclude():
    class MyMutation(MutationType, model=Task, exclude=["name"]): ...

    assert sorted(MyMutation.__input_map__) == [
        "acceptancecriteria",
        "assignees",
        "comments",
        "objective",
        "pk",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
    ]

    input_type = MyMutation.__input_type__()
    assert sorted(input_type.fields) == [
        "acceptancecriteria",
        "assignees",
        "comments",
        "objective",
        "pk",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
    ]


def test_mutation_type__exclude__multiple():
    class MyMutation(MutationType, model=Task, exclude=["name", "pk"]): ...

    assert sorted(MyMutation.__input_map__) == [
        "acceptancecriteria",
        "assignees",
        "comments",
        "objective",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
    ]

    input_type = MyMutation.__input_type__()
    assert sorted(input_type.fields) == [
        "acceptancecriteria",
        "assignees",
        "comments",
        "objective",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
    ]


def test_mutation_type__typename():
    class MyMutation(MutationType, model=Task, typename="CustomName"): ...

    assert MyMutation.__typename__ == "CustomName"

    input_type = MyMutation.__input_type__()
    assert input_type.name == "CustomName"


def test_mutation_type__extensions():
    class MyMutation(MutationType, model=Task, extensions={"foo": "bar"}): ...

    assert MyMutation.__extensions__ == {"foo": "bar", "undine_mutation": MyMutation}

    input_type = MyMutation.__input_type__()
    assert input_type.extensions == {"foo": "bar", "undine_mutation": MyMutation}


def test_mutation_type__validate():
    class MyMutation(MutationType, model=Task):
        @classmethod
        def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
            if input_data["foo"] is not True:
                msg = "Foo must be True"
                raise ValueError(msg)

    MyMutation.__validate__(MockGQLInfo(), {"foo": True})

    with pytest.raises(ValueError, match=exact("Foo must be True")):
        MyMutation.__validate__(MockGQLInfo(), {"foo": False})
