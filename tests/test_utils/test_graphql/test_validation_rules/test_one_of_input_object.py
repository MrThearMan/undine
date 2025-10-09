from __future__ import annotations

import pytest

from example_project.app.models import Comment, Project, Task, TaskTypeChoices
from undine import Entrypoint, Field, Input, MutationType, QueryType, RootType, create_schema


@pytest.mark.django_db
def test_validation_rules__one_of_input_object__multiple_keys(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class ProjectType(QueryType[Project]):
        name = Field()

    class CommentType(QueryType[Comment]):
        contents = Field()
        target = Field()

    class CommentCreateMutation(MutationType[Comment]):
        contents = Input()
        target = Input()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    class Mutation(RootType):
        create_comment = Entrypoint(CommentCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation($input: CommentCreateMutation!) {
            createComment(input: $input) {
                contents
                target {
                    __typename
                    ... on TaskType {
                        name
                    }
                    ... on ProjectType {
                        name
                    }
                }
            }
        }
    """

    input_data = {
        "contents": "Comment",
        "target": {
            "task": {
                "name": "Test Task",
                "type": TaskTypeChoices.TASK,
            },
            "project": {
                "name": "Test Project",
            },
        },
    }
    response = graphql(query, variables={"input": input_data})

    assert response.errors == [
        {
            "message": "OneOf Input Object 'CommentTargetInput' must specify exactly one key.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_validation_rules__one_of_input_object__null_key(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class CommentType(QueryType[Comment]):
        contents = Field()
        target = Field()

    class CommentCreateMutation(MutationType[Comment]):
        contents = Input()
        target = Input()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    class Mutation(RootType):
        create_comment = Entrypoint(CommentCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation($input: CommentCreateMutation!) {
            createComment(input: $input) {
                contents
                target {
                    __typename
                    ... on TaskType {
                        name
                    }
                }
            }
        }
    """

    input_data = {
        "contents": "Comment",
        "target": {
            "task": None,
        },
    }
    response = graphql(query, variables={"input": input_data})

    assert response.errors == [
        {
            "message": "Field 'CommentTargetInput.task' must be non-null.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_validation_rules__one_of_input_object__multiple_keys__document(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class ProjectType(QueryType[Project]):
        name = Field()

    class CommentType(QueryType[Comment]):
        contents = Field()
        target = Field()

    class CommentCreateMutation(MutationType[Comment]):
        contents = Input()
        target = Input()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    class Mutation(RootType):
        create_comment = Entrypoint(CommentCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation {
            createComment(
                input: {
                    contents: "Comment"
                    target: {
                        task: {
                            name: "Test Task"
                            type: TASK
                        }
                        project: {
                            name: "Test Project"
                        }
                    }
                }
            ) {
                contents
                target {
                    __typename
                    ... on TaskType {
                        name
                    }
                    ... on ProjectType {
                        name
                    }
                }
            }
        }
    """

    response = graphql(query)

    assert response.errors == [
        {
            "message": "OneOf Input Object 'CommentTargetInput' must specify exactly one key.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_validation_rules__one_of_input_object__null_key__document(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class CommentType(QueryType[Comment]):
        contents = Field()
        target = Field()

    class CommentCreateMutation(MutationType[Comment]):
        contents = Input()
        target = Input()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    class Mutation(RootType):
        create_comment = Entrypoint(CommentCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation {
            createComment(
                input: {
                    contents: "Comment"
                    target: {
                        task: null
                    }
                }
            ) {
                contents
                target {
                    __typename
                    ... on TaskType {
                        name
                    }
                }
            }
        }
    """

    response = graphql(query)

    assert response.errors == [
        {
            "message": "Field 'CommentTargetInput.task' must be non-null.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_validation_rules__one_of_input_object__null_key__document_variable(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class CommentType(QueryType[Comment]):
        contents = Field()
        target = Field()

    class CommentCreateMutation(MutationType[Comment]):
        contents = Input()
        target = Input()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    class Mutation(RootType):
        create_comment = Entrypoint(CommentCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($target: CommentTargetTaskInput!) {
            createComment(
                input: {
                    contents: "Comment"
                    target: {
                        task: $target
                    }
                }
            ) {
                contents
                target {
                    __typename
                    ... on TaskType {
                        name
                    }
                }
            }
        }
    """

    response = graphql(query, variables={"target": None})

    assert response.errors == [
        {
            "message": "Variable '$target' of non-null type 'CommentTargetTaskInput!' must not be null.",
            "extensions": {"status_code": 400},
        }
    ]
