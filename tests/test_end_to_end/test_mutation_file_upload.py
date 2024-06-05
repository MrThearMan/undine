from __future__ import annotations

from io import BytesIO

import pytest
from django.core.files import File

from example_project.app.models import Task
from tests.helpers import create_png
from undine import Entrypoint, Field, Input, MutationType, QueryType, RootType, create_schema


@pytest.mark.django_db
def test_end_to_end__mutation__file_upload(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        attachment = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        attachment = Input()

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
            attachment
          }
        }
    """

    file = File(BytesIO(b""), name="file.txt")

    data = {
        "name": "Test task",
        "attachment": file,
    }

    response = graphql.query(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.json == {
        "data": {
            "createTask": {
                "name": "Test task",
                "attachment": "/media/file.txt",
            },
        },
    }


@pytest.mark.django_db
def test_end_to_end__mutation__image_upload(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        image = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        image = Input()

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
            image
          }
        }
    """

    image = create_png()

    data = {
        "name": "Test task",
        "image": image,
    }

    response = graphql.query(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.json == {
        "data": {
            "createTask": {
                "name": "Test task",
                "image": "/media/image.png",
            },
        },
    }


@pytest.mark.django_db
def test_end_to_end__mutation__image_upload__not_image(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        image = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        image = Input()

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
            image
          }
        }
    """

    image = File(BytesIO(b""), name="image.png")

    data = {
        "name": "Test task",
        "image": image,
    }

    response = graphql.query(query, variables={"input": data})

    assert response.error_message(0) == (
        "Variable '$input' got invalid value <InMemoryUploadedFile instance> at 'input.image'; "
        "'Image' cannot represent value <InMemoryUploadedFile instance>: "
        "File either not an image or a corrupted image."
    )
