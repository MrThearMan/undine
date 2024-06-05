from __future__ import annotations

from graphql import GraphQLArgument, GraphQLInputObjectType, GraphQLList, GraphQLNonNull, GraphQLObjectType

from example_project.app.models import Task
from undine import Entrypoint, MutationType, QueryType, RootType
from undine.resolvers import BulkCreateResolver, CreateResolver


def test_entrypoint__mutation_type__repr() -> None:
    class TaskCreateMutation(MutationType[Task]): ...

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    assert repr(Mutation.create_task) == f"<undine.entrypoint.Entrypoint(ref={TaskCreateMutation!r})>"


def test_entrypoint__mutation__attributes() -> None:
    class TaskCreateMutation(MutationType[Task]):
        """Mutation description."""

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    assert Mutation.create_task.ref == TaskCreateMutation
    assert Mutation.create_task.many is False
    assert Mutation.create_task.description == "Mutation description."
    assert Mutation.create_task.deprecation_reason is None
    assert Mutation.create_task.extensions == {"undine_entrypoint": Mutation.create_task}
    assert Mutation.create_task.root_type == Mutation
    assert Mutation.create_task.name == "create_task"


def test_entrypoint__mutation__get_field_type() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    field_type = Mutation.create_task.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLObjectType)
    assert field_type.of_type == TaskType.__output_type__()


def test_entrypoint__mutation__get_field_arguments() -> None:
    class TaskCreateMutation(MutationType[Task]):
        """Mutation description."""

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    arguments = Mutation.create_task.get_field_arguments()
    assert sorted(arguments) == ["input"]
    assert isinstance(arguments["input"], GraphQLArgument)
    assert isinstance(arguments["input"].type, GraphQLNonNull)
    assert isinstance(arguments["input"].type.of_type, GraphQLInputObjectType)


def test_entrypoint__mutation__get_resolver() -> None:
    class TaskCreateMutation(MutationType[Task]): ...

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    resolver = Mutation.create_task.get_resolver()
    assert isinstance(resolver, CreateResolver)


def test_entrypoint__mutation__as_graphql_field() -> None:
    class TaskType(QueryType[Task]):
        """Query Description."""

    class TaskCreateMutation(MutationType[Task]):
        """Mutation description."""

    class Mutation(RootType):
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


def test_entrypoint__mutation__many() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation, many=True)

    assert Mutation.create_task.ref == TaskCreateMutation
    assert Mutation.create_task.many is True

    field_type = Mutation.create_task.get_field_type()
    assert isinstance(field_type, GraphQLNonNull)
    assert isinstance(field_type.of_type, GraphQLList)
    assert isinstance(field_type.of_type.of_type, GraphQLNonNull)
    assert isinstance(field_type.of_type.of_type.of_type, GraphQLObjectType)
    assert field_type.of_type.of_type.of_type == TaskType.__output_type__()

    resolver = Mutation.create_task.get_resolver()
    assert isinstance(resolver, BulkCreateResolver)
