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
from undine.resolvers import CreateResolver, FunctionResolver


def test_entrypoint__query():
    class TaskType(QueryType, model=Task): ...

    class Query:
        task = Entrypoint(TaskType)

    task = Query.task

    assert repr(task) == f"<undine.schema.Entrypoint(ref={TaskType})>"

    assert task.ref == TaskType
    assert task.many is False
    assert task.description is None
    assert task.deprecation_reason is None
    assert task.extensions == {"undine_entrypoint": task}

    assert task.owner == Query
    assert task.name == "task"

    field_type = task.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLObjectType)

    arguments = task.get_field_arguments()
    assert arguments == {"pk": GraphQLArgument(GraphQLInt)}

    resolver = task.get_resolver()
    assert resolver == TaskType.__resolve_one__

    graphql_field = task.as_graphql_field()

    assert isinstance(graphql_field.type, GraphQLNonNull)
    assert isinstance(graphql_field.type.of_type, GraphQLObjectType)

    assert graphql_field.args == {"pk": GraphQLArgument(GraphQLInt)}

    assert graphql_field.resolve == TaskType.__resolve_one__
    assert graphql_field.description is None
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_entrypoint": task}


def test_entrypoint__query__description():
    class TaskType(QueryType, model=Task):
        """Description."""

    class Query:
        foo = Entrypoint(TaskType)

    assert Query.foo.description == "Description."


def test_entrypoint__query__many():
    class TaskType(QueryType, model=Task, filterset=True, orderset=True): ...

    class Query:
        foo = Entrypoint(TaskType, many=True)

    assert Query.foo.many is True

    field_type = Query.foo.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLList)
    assert isinstance(field_type.of_type.of_type, GraphQLNonNull)
    assert isinstance(field_type.of_type.of_type.of_type, GraphQLObjectType)

    arguments = Query.foo.get_field_arguments()
    assert sorted(arguments) == ["filter", "orderBy"]

    assert isinstance(arguments["filter"], GraphQLArgument)
    assert isinstance(arguments["filter"].type, GraphQLInputObjectType)

    assert isinstance(arguments["orderBy"], GraphQLArgument)
    assert isinstance(arguments["orderBy"].type, GraphQLList)
    assert isinstance(arguments["orderBy"].type.of_type, GraphQLNonNull)
    assert isinstance(arguments["orderBy"].type.of_type.of_type, GraphQLEnumType)

    resolver = Query.foo.get_resolver()
    assert resolver == TaskType.__resolve_many__


def test_entrypoint__mutation():
    class TaskType(QueryType, model=Task): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation)

    task = Mutation.create_task

    assert repr(task) == f"<undine.schema.Entrypoint(ref={TaskCreateMutation})>"

    assert task.ref == TaskCreateMutation
    assert task.many is False
    assert task.description is None
    assert task.deprecation_reason is None
    assert task.extensions == {"undine_entrypoint": task}

    assert task.owner == Mutation
    assert task.name == "create_task"

    field_type = task.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLObjectType)
    assert field_type.of_type == TaskType.__output_type__()

    arguments = task.get_field_arguments()
    assert sorted(arguments) == ["input"]
    assert isinstance(arguments["input"], GraphQLArgument)
    assert isinstance(arguments["input"].type, GraphQLNonNull)
    assert isinstance(arguments["input"].type.of_type, GraphQLInputObjectType)

    resolver = task.get_resolver()
    assert isinstance(resolver, CreateResolver)

    graphql_field = task.as_graphql_field()

    assert isinstance(graphql_field.type, GraphQLNonNull)
    assert isinstance(graphql_field.type.of_type, GraphQLObjectType)
    assert graphql_field.type.of_type == TaskType.__output_type__()

    assert sorted(graphql_field.args) == ["input"]
    assert isinstance(graphql_field.args["input"], GraphQLArgument)
    assert isinstance(graphql_field.args["input"].type, GraphQLNonNull)
    assert isinstance(graphql_field.args["input"].type.of_type, GraphQLInputObjectType)

    assert isinstance(graphql_field.resolve, CreateResolver)
    assert graphql_field.description is None
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_entrypoint": task}


def test_entrypoint__mutation__description():
    class TaskType(QueryType, model=Task):
        """Description."""

    class TaskCreateMutation(MutationType, model=Task):
        """Mutation description."""

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation)

    assert Mutation.create_task.description == "Mutation description."


@pytest.mark.skip("Not implemented yet")
def test_entrypoint__mutation__many():
    class TaskType(QueryType, model=Task):
        """Description."""

    class TaskCreateMutation(MutationType, model=Task):
        """Mutation description."""

    class Mutation:
        create_task = Entrypoint(TaskCreateMutation, many=True)


def test_entrypoint__missing_reference():
    with pytest.raises(MissingEntrypointRefError):

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
            return number * 2

    double = Query.double

    assert callable(double.ref)
    assert double.many is False
    assert double.description is None
    assert double.deprecation_reason is None
    assert double.extensions == {"undine_entrypoint": double}

    assert double.owner == Query
    assert double.name == "double"

    field_type = double.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert field_type.of_type == GraphQLInt

    arguments = double.get_field_arguments()
    assert isinstance(arguments["number"], GraphQLArgument)
    assert isinstance(arguments["number"].type, GraphQLNonNull)
    assert arguments["number"].type.of_type, GraphQLInt

    resolver = double.get_resolver()
    assert isinstance(resolver, FunctionResolver)

    graphql_field = double.as_graphql_field()

    assert isinstance(graphql_field.type, GraphQLNonNull)
    assert graphql_field.type.of_type == GraphQLInt

    assert isinstance(graphql_field.args["number"], GraphQLArgument)
    assert isinstance(graphql_field.args["number"].type, GraphQLNonNull)
    assert graphql_field.args["number"].type.of_type, GraphQLInt

    assert isinstance(graphql_field.resolve, FunctionResolver)
    assert graphql_field.description is None
    assert graphql_field.deprecation_reason is None
    assert graphql_field.extensions == {"undine_entrypoint": double}


def test_entrypoint__function__arguments():
    class Query:
        @Entrypoint(description="Description.")
        def double(self, number: int) -> int:
            return number * 2

    double = Query.double
    assert double.description == "Description."
