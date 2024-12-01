import sys

import pytest
from graphql import (
    GraphQLArgument,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
)

from example_project.app.models import Task
from undine import Entrypoint, MutationType, QueryType
from undine.errors.exceptions import MissingEntrypointRefError
from undine.resolvers import CreateResolver, FunctionResolver, ModelManyResolver, ModelSingleResolver


def test_entrypoint__query__repr():
    class TaskType(QueryType, model=Task):
        """Description."""

    class Query:
        task = Entrypoint(TaskType)

    assert repr(Query.task) == f"<undine.schema.Entrypoint(ref={TaskType})>"


def test_entrypoint__query__attributes():
    class TaskType(QueryType, model=Task):
        """Description."""

    class Query:
        task = Entrypoint(TaskType)

    assert Query.task.ref == TaskType
    assert Query.task.many is False
    assert Query.task.description == "Description."
    assert Query.task.deprecation_reason is None
    assert Query.task.extensions == {"undine_entrypoint": Query.task}
    assert Query.task.owner == Query
    assert Query.task.name == "task"


def test_entrypoint__query__get_field_type():
    class TaskType(QueryType, model=Task):
        """Description."""

    class Query:
        task = Entrypoint(TaskType)

    field_type = Query.task.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLObjectType)


def test_entrypoint__query__get_field_arguments():
    class TaskType(QueryType, model=Task):
        """Description."""

    class Query:
        task = Entrypoint(TaskType)

    arguments = Query.task.get_field_arguments()

    assert arguments == {"pk": GraphQLArgument(GraphQLNonNull(GraphQLInt))}


def test_entrypoint__query__get_resolver():
    class TaskType(QueryType, model=Task):
        """Description."""

    class Query:
        task = Entrypoint(TaskType)

    resolver = Query.task.get_resolver()
    assert isinstance(resolver, ModelSingleResolver)


def test_entrypoint__query__as_graphql_field():
    class TaskType(QueryType, model=Task):
        """Description."""

    class Query:
        task = Entrypoint(TaskType)

    graphql_field = Query.task.as_graphql_field()

    assert isinstance(graphql_field.type, GraphQLNonNull)
    assert isinstance(graphql_field.type.of_type, GraphQLObjectType)

    assert graphql_field.args == {"pk": GraphQLArgument(GraphQLNonNull(GraphQLInt))}
    assert isinstance(graphql_field.resolve, ModelSingleResolver)
    assert graphql_field.description == "Description."
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_entrypoint": Query.task}


def test_entrypoint__query__many__attributes():
    class TaskType(QueryType, model=Task, filterset=True, orderset=True):
        """Description."""

    class Query:
        task = Entrypoint(TaskType, many=True)

    assert Query.task.ref == TaskType
    assert Query.task.many is True
    assert Query.task.description == "Description."
    assert Query.task.deprecation_reason is None
    assert Query.task.extensions == {"undine_entrypoint": Query.task}
    assert Query.task.owner == Query
    assert Query.task.name == "task"


def test_entrypoint__query__many__get_field_type():
    class TaskType(QueryType, model=Task, filterset=True, orderset=True):
        """Description."""

    class Query:
        task = Entrypoint(TaskType, many=True)

    field_type = Query.task.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLList)
    assert isinstance(field_type.of_type.of_type, GraphQLNonNull)
    assert isinstance(field_type.of_type.of_type.of_type, GraphQLObjectType)


def test_entrypoint__query__many__get_field_arguments():
    class TaskType(QueryType, model=Task, filterset=True, orderset=True):
        """Description."""

    class Query:
        task = Entrypoint(TaskType, many=True)

    arguments = Query.task.get_field_arguments()
    assert sorted(arguments) == ["filter", "orderBy"]

    assert isinstance(arguments["filter"], GraphQLArgument)
    assert isinstance(arguments["filter"].type, GraphQLInputObjectType)

    assert isinstance(arguments["orderBy"], GraphQLArgument)
    assert isinstance(arguments["orderBy"].type, GraphQLList)
    assert isinstance(arguments["orderBy"].type.of_type, GraphQLNonNull)
    assert isinstance(arguments["orderBy"].type.of_type.of_type, GraphQLEnumType)


def test_entrypoint__query__many__get_resolver():
    class TaskType(QueryType, model=Task, filterset=True, orderset=True): ...

    class Query:
        task = Entrypoint(TaskType, many=True)

    resolver = Query.task.get_resolver()
    assert isinstance(resolver, ModelManyResolver)


def test_entrypoint__mutation__repr():
    class TaskCreateMutation(MutationType, model=Task): ...

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation)

    assert repr(Mutation.create_task) == f"<undine.schema.Entrypoint(ref={TaskCreateMutation})>"


def test_entrypoint__mutation__attributes():
    class TaskCreateMutation(MutationType, model=Task):
        """Mutation description."""

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation)

    assert Mutation.create_task.ref == TaskCreateMutation
    assert Mutation.create_task.many is False
    assert Mutation.create_task.description == "Mutation description."
    assert Mutation.create_task.deprecation_reason is None
    assert Mutation.create_task.extensions == {"undine_entrypoint": Mutation.create_task}
    assert Mutation.create_task.owner == Mutation
    assert Mutation.create_task.name == "create_task"


def test_entrypoint__mutation__get_field_type():
    class TaskType(QueryType, model=Task): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation)

    field_type = Mutation.create_task.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLObjectType)
    assert field_type.of_type == TaskType.__output_type__()


def test_entrypoint__mutation__get_field_arguments():
    class TaskCreateMutation(MutationType, model=Task):
        """Mutation description."""

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation)

    arguments = Mutation.create_task.get_field_arguments()
    assert sorted(arguments) == ["input"]
    assert isinstance(arguments["input"], GraphQLArgument)
    assert isinstance(arguments["input"].type, GraphQLNonNull)
    assert isinstance(arguments["input"].type.of_type, GraphQLInputObjectType)


def test_entrypoint__mutation__get_resolver():
    class TaskCreateMutation(MutationType, model=Task): ...

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation)

    resolver = Mutation.create_task.get_resolver()
    assert isinstance(resolver, CreateResolver)


def test_entrypoint__mutation__as_graphql_field():
    class TaskType(QueryType, model=Task):
        """Query Description."""

    class TaskCreateMutation(MutationType, model=Task):
        """Mutation description."""

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation)

    graphql_field = Mutation.create_task.as_graphql_field()
    assert isinstance(graphql_field.type, GraphQLNonNull)
    assert isinstance(graphql_field.type.of_type, GraphQLObjectType)
    assert graphql_field.type.of_type == TaskType.__output_type__()

    assert sorted(graphql_field.args) == ["input"]
    assert isinstance(graphql_field.args["input"], GraphQLArgument)
    assert isinstance(graphql_field.args["input"].type, GraphQLNonNull)
    assert isinstance(graphql_field.args["input"].type.of_type, GraphQLInputObjectType)

    assert isinstance(graphql_field.resolve, CreateResolver)
    assert graphql_field.description == "Mutation description."
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_entrypoint": Mutation.create_task}


# TODO: 'test_entrypoint__mutation__many'


def test_entrypoint__missing_reference():
    error = MissingEntrypointRefError if sys.version_info >= (3, 12) else RuntimeError

    with pytest.raises(error):

        class Query:
            foo = Entrypoint()


def test_entrypoint__description_in_entrypoint():
    class TaskType(QueryType, model=Task):
        """Description."""

    class Query:
        foo = Entrypoint(TaskType, description="Actual description.")

    assert Query.foo.description == "Actual description."


def test_entrypoint__deprecation_reason():
    class TaskType(QueryType, model=Task): ...

    class Query:
        foo = Entrypoint(TaskType, deprecation_reason="Use something else.")

    assert Query.foo.deprecation_reason == "Use something else."


def test_entrypoint__function():
    class Query:
        @Entrypoint
        def double(self, number: int) -> int:
            """Description."""
            return number * 2

    assert repr(Query.double) == f"<undine.schema.Entrypoint(ref={Query.double.ref})>"


def test_entrypoint__function__attributes():
    class Query:
        @Entrypoint
        def double(self, number: int) -> int:
            """Description."""
            return number * 2

    assert callable(Query.double.ref)
    assert Query.double.many is False
    assert Query.double.description == "Description."
    assert Query.double.deprecation_reason is None
    assert Query.double.extensions == {"undine_entrypoint": Query.double}
    assert Query.double.owner == Query
    assert Query.double.name == "double"


def test_entrypoint__function__get_field_type():
    class Query:
        @Entrypoint
        def double(self, number: int) -> int:
            """Description."""
            return number * 2

    field_type = Query.double.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLInt)


def test_entrypoint__function__get_field_arguments():
    class Query:
        @Entrypoint
        def double(self, number: int) -> int:
            """Description."""
            return number * 2

    arguments = Query.double.get_field_arguments()
    assert arguments == {"number": GraphQLArgument(GraphQLNonNull(GraphQLInt))}


def test_entrypoint__function__get_resolver():
    class Query:
        @Entrypoint
        def double(self, number: int) -> int:
            """Description."""
            return number * 2

    resolver = Query.double.get_resolver()
    assert isinstance(resolver, FunctionResolver)


def test_entrypoint__function__as_graphql_field():
    class Query:
        @Entrypoint
        def double(self, number: int) -> int:
            """Description."""
            return number * 2

    graphql_field = Query.double.as_graphql_field()

    assert graphql_field.type == GraphQLNonNull(GraphQLInt)
    assert graphql_field.args == {"number": GraphQLArgument(GraphQLNonNull(GraphQLInt))}
    assert isinstance(graphql_field.resolve, FunctionResolver)
    assert graphql_field.description == "Description."
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_entrypoint": Query.double}


def test_entrypoint__function__decorator_arguments():
    class Query:
        @Entrypoint(deprecation_reason="Use something else.")
        def double(self, number: int) -> int:
            return number * 2

    assert Query.double.deprecation_reason == "Use something else."
