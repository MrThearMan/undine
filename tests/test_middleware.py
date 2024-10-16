import contextlib
import logging
from copy import deepcopy

import pytest

from example_project.app.models import Comment, Person, Project, ServiceRequest, Task, TaskTypeChoices, Team
from tests.helpers import MockGQLInfo, exact
from undine import Input, MutationType
from undine.middleware import MutationMiddlewareContext, RemoveInputOnlyFieldsMiddleware, error_logging_middleware


def test_error_logging_middleware(caplog):
    caplog.set_level(logging.DEBUG, logger="undine")

    def func(*args, **kwargs):
        msg = "Test"
        raise ValueError(msg)

    with pytest.raises(ValueError, match=exact("Test")):
        error_logging_middleware(func, root=None, info=MockGQLInfo())

    assert caplog.record_tuples[0][0] == "undine"
    assert caplog.record_tuples[0][1] == logging.ERROR
    assert "ValueError: Test" in caplog.record_tuples[0][2]


def test_remove_input_only_fields_middleware():
    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input(input_only=True)
        type = Input()
        created_at = Input()

    input_data = {
        "name": "foo",
        "type": TaskTypeChoices.STORY.value,
        "createdAt": "2022-01-01T00:00:00",
    }

    middleware = RemoveInputOnlyFieldsMiddleware(
        mutation_type=MyMutationType,
        info=MockGQLInfo(),
        input_data=deepcopy(input_data),
    )

    it = iter(middleware)

    with contextlib.suppress(StopIteration):
        next(it)

    assert middleware.input_data == {
        "type": TaskTypeChoices.STORY.value,
        "createdAt": "2022-01-01T00:00:00",
    }

    with contextlib.suppress(StopIteration):
        next(it)

    assert middleware.input_data == input_data


def test_remove_input_only_fields_middleware__nested():
    class MyTeamType(MutationType, model=Team, auto=False):
        name = Input()

    class MyCommentType(MutationType, model=Comment, auto=False):
        contents = Input(input_only=True)

    class MyProjectType(MutationType, model=Project, auto=False):
        pk = Input()
        name = Input(input_only=True)
        team = Input(MyTeamType, input_only=True)
        comments = Input(MyCommentType, many=True)

    class MyServiceRequestType(MutationType, model=ServiceRequest, auto=False):
        details = Input(input_only=True)

    class AssgneeType(MutationType, model=Person, auto=False):
        name = Input()
        email = Input(input_only=True)

    class MyTaskType(MutationType, model=Task, auto=False):
        name = Input(input_only=True)
        type = Input()
        created_at = Input()

        project = Input(MyProjectType)
        request = Input(MyServiceRequestType)
        assignees = Input(AssgneeType, many=True)

    input_data = {
        "name": "foo",
        "type": TaskTypeChoices.STORY.value,
        "createdAt": "2022-01-01T00:00:00",
        "request": {
            "details": "Test request",
        },
        "project": {
            "pk": 1,
            "name": "Test project",
            "team": {
                "pk": 2,
                "name": "Test team",
            },
            "comments": [
                {
                    "contents": "Test comment",
                },
            ],
        },
        "assignees": [
            {
                "name": "Test user",
                "email": "test@user.com",
            },
        ],
    }

    middleware = RemoveInputOnlyFieldsMiddleware(
        mutation_type=MyTaskType,
        info=MockGQLInfo(),
        input_data=deepcopy(input_data),
    )

    it = iter(middleware)

    with contextlib.suppress(StopIteration):
        next(it)

    assert middleware.input_data == {
        "type": TaskTypeChoices.STORY.value,
        "createdAt": "2022-01-01T00:00:00",
        "project": {"pk": 1, "comments": [{}]},
        "request": {},
        "assignees": [{"name": "Test user"}],
    }

    with contextlib.suppress(StopIteration):
        next(it)

    assert middleware.input_data == input_data


def test_mutation_middleware_context():
    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input(input_only=True)
        type = Input()
        created_at = Input()

    input_data = {
        "name": "foo",
        "type": TaskTypeChoices.STORY.value,
        "createdAt": "2022-01-01T00:00:00",
    }

    copy_data = deepcopy(input_data)

    with MutationMiddlewareContext(mutation_type=MyMutationType, info=MockGQLInfo(), input_data=copy_data):
        assert copy_data == {
            "type": TaskTypeChoices.STORY.value,
            "createdAt": "2022-01-01T00:00:00",
        }

    assert copy_data == input_data
