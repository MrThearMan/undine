from example_project.app.models import Task
from undine import MutationType, QueryType
from undine.mutation import DeleteMutationOutputType


def test_mutation_type__default():
    class MyQueryType(QueryType, model=Task): ...

    class MyCreateMutation(MutationType, model=Task):
        """Description."""

    assert MyCreateMutation.__model__ == Task
    assert MyCreateMutation.__lookup_field__ == "pk"
    assert MyCreateMutation.__mutation_kind__ == "create"
    assert MyCreateMutation.__typename__ == "MyCreateMutation"
    assert MyCreateMutation.__extensions__ == {"undine_mutation": MyCreateMutation}

    assert sorted(MyCreateMutation.__input_map__) == [
        "assignees",
        "name",
        "project",
        "relatedTasks",
        "request",
        "type",
    ]

    input_type = MyCreateMutation.__input_type__()
    assert input_type.name == "MyCreateMutation"
    assert input_type.description == "Description."
    assert input_type.extensions == {"undine_mutation": MyCreateMutation}

    assert sorted(input_type.fields) == [
        "assignees",
        "name",
        "project",
        "relatedTasks",
        "request",
        "type",
    ]

    output_type = MyCreateMutation.__output_type__()
    assert output_type == MyQueryType.__output_type__()


def test_mutation_type__mutation_kind__create():
    class MyQueryType(QueryType, model=Task): ...

    # Determined from name.
    class MyCreateMutation(MutationType, model=Task): ...

    assert MyCreateMutation.__mutation_kind__ == "create"

    # Set explicitly.
    class MyMutation(MutationType, model=Task, mutation_kind="create"): ...

    assert MyMutation.__mutation_kind__ == "create"

    # Primary key not included in create mutations.
    assert MyMutation.__lookup_field__ not in MyMutation.__input_map__

    output_type = MyMutation.__output_type__()
    assert output_type == MyQueryType.__output_type__()


def test_mutation_type__mutation_kind__update():
    class MyQueryType(QueryType, model=Task): ...

    # Determined from name.
    class MyUpdateMutation(MutationType, model=Task): ...

    assert MyUpdateMutation.__mutation_kind__ == "update"

    # Set explicitly.
    class MyMutation(MutationType, model=Task, mutation_kind="update"): ...

    assert MyMutation.__mutation_kind__ == "update"

    # Primary key included in create mutations.
    assert MyMutation.__lookup_field__ in MyMutation.__input_map__

    output_type = MyMutation.__output_type__()
    assert output_type == MyQueryType.__output_type__()


def test_mutation_type__mutation_kind__delete():
    class MyQueryType(QueryType, model=Task): ...

    # Determined from name.
    class MyDeleteMutation(MutationType, model=Task): ...

    assert MyDeleteMutation.__mutation_kind__ == "delete"

    # Set explicitly.
    class MyMutation(MutationType, model=Task, mutation_kind="delete"): ...

    assert MyMutation.__mutation_kind__ == "delete"

    # Primary key included in create mutations.
    assert MyMutation.__lookup_field__ in MyMutation.__input_map__

    output_type = MyMutation.__output_type__()
    assert output_type == DeleteMutationOutputType


def test_mutation_type__mutation_kind__custom():
    class MyQueryType(QueryType, model=Task): ...

    # Determined from name, since doesn't contain "create", "update", or "delete".
    class MyOtherMutation(MutationType, model=Task): ...

    assert MyOtherMutation.__mutation_kind__ == "custom"

    # Set explicitly (even if name contains "create", "update", or "delete").
    class MyCreateMutation(MutationType, model=Task, mutation_kind="custom"): ...

    assert MyCreateMutation.__mutation_kind__ == "custom"

    # Primary key included not in create mutations.
    assert MyCreateMutation.__lookup_field__ in MyCreateMutation.__input_map__

    output_type = MyCreateMutation.__output_type__()
    assert output_type == MyQueryType.__output_type__()


def test_mutation_type__auto():
    class MyMutation(MutationType, model=Task, auto=False): ...

    assert MyMutation.__input_map__ == {}


def test_mutation_type__exclude():
    class MyMutation(MutationType, model=Task, exclude=["name"]): ...

    assert sorted(MyMutation.__input_map__) == [
        "assignees",
        "pk",
        "project",
        "relatedTasks",
        "request",
        "type",
    ]

    input_type = MyMutation.__input_type__()
    assert sorted(input_type.fields) == [
        "assignees",
        "pk",
        "project",
        "relatedTasks",
        "request",
        "type",
    ]


def test_mutation_type__exclude__multiple():
    class MyMutation(MutationType, model=Task, exclude=["name", "pk"]): ...

    assert sorted(MyMutation.__input_map__) == [
        "assignees",
        "project",
        "relatedTasks",
        "request",
        "type",
    ]

    input_type = MyMutation.__input_type__()
    assert sorted(input_type.fields) == [
        "assignees",
        "project",
        "relatedTasks",
        "request",
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
