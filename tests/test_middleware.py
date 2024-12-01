from __future__ import annotations

import itertools
import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Self

import pytest

from example_project.app.models import Comment, Person, Project, ServiceRequest, Task, TaskTypeChoices, Team
from tests.factories import UserFactory
from tests.helpers import MockGQLInfo, MockRequest, exact
from undine import Input, MutationType
from undine.dataclasses import MutationMiddlewareParams
from undine.middleware import (
    InputDataModificationMiddleware,
    InputDataValidationMiddleware,
    InputOnlyDataRemovalMiddleware,
    MutationMiddleware,
    MutationMiddlewareHandler,
    PostMutationHandlingMiddleware,
    error_logging_middleware,
)

if TYPE_CHECKING:
    from undine.typing import GQLInfo


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


def test_input_data_modification_middleware():
    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input(hidden=True, default_value="foo")

        @Input
        def current_user_id(self: Input, info: GQLInfo) -> int | None:
            return info.context.user.id

    input_data = {}

    middleware = InputDataModificationMiddleware(
        params=MutationMiddlewareParams(
            mutation_type=MyMutationType,
            info=MockGQLInfo(context=MockRequest(user=UserFactory.build(id=1))),
            input_data=deepcopy(input_data),
        ),
    )

    with middleware:
        assert middleware.params.input_data == {
            "name": "foo",
            "current_user_id": 1,
        }


def test_input_data_validation_middleware():
    counter = itertools.count(1)
    validate_called = -1
    validator_1_called = -1
    validator_2_called = -1

    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input(input_only=True)
        type = Input()
        created_at = Input()

        @name.validate
        def _(self, info: GQLInfo, value: str) -> None:
            nonlocal validator_1_called
            validator_1_called = next(counter)

        @type.validate
        def _(self, info: GQLInfo, value: str) -> None:
            nonlocal validator_2_called
            validator_2_called = next(counter)

        @classmethod
        def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validate_called
            validate_called = next(counter)

    input_data = {
        "name": "foo",
        "type": TaskTypeChoices.STORY.value,
        "created_at": "2022-01-01T00:00:00",
    }

    middleware = InputDataValidationMiddleware(
        params=MutationMiddlewareParams(
            mutation_type=MyMutationType,
            info=MockGQLInfo(),
            input_data=deepcopy(input_data),
        ),
    )

    with middleware:
        assert validator_1_called == 1
        assert validator_2_called == 2
        assert validate_called == 3


def test_post_mutation_handling_middleware():
    post_handler_called = False

    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input()

        @classmethod
        def __post_handle__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal post_handler_called
            post_handler_called = True

    input_data = {
        "name": "foo",
    }

    middleware = PostMutationHandlingMiddleware(
        params=MutationMiddlewareParams(
            mutation_type=MyMutationType,
            info=MockGQLInfo(),
            input_data=deepcopy(input_data),
        ),
    )

    with middleware:
        assert post_handler_called is False

    assert post_handler_called is True


def test_input_only_data_removal_middleware():
    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input(input_only=True)
        type = Input()
        created_at = Input()

    input_data = {
        "name": "foo",
        "type": TaskTypeChoices.STORY.value,
        "created_at": "2022-01-01T00:00:00",
    }

    middleware = InputOnlyDataRemovalMiddleware(
        params=MutationMiddlewareParams(
            mutation_type=MyMutationType,
            info=MockGQLInfo(),
            input_data=deepcopy(input_data),
        ),
    )

    with middleware:
        assert middleware.params.input_data == {
            "type": TaskTypeChoices.STORY.value,
            "created_at": "2022-01-01T00:00:00",
        }

    assert middleware.params.input_data == input_data


def test_input_only_data_removal_middleware__nested():
    class MyTeamType(MutationType, model=Team, auto=False):
        pk = Input()
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

        project = Input(MyProjectType)
        request = Input(MyServiceRequestType)
        assignees = Input(AssgneeType, many=True)

    input_data = {
        "name": "foo",
        "type": TaskTypeChoices.STORY.value,
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

    middleware = InputOnlyDataRemovalMiddleware(
        params=MutationMiddlewareParams(
            mutation_type=MyTaskType,
            info=MockGQLInfo(),
            input_data=deepcopy(input_data),
        ),
    )

    with middleware:
        assert middleware.params.input_data == {
            "type": TaskTypeChoices.STORY.value,
            "project": {"pk": 1, "comments": [{}]},
            "request": {},
            "assignees": [{"name": "Test user"}],
        }

    assert middleware.params.input_data == input_data


@pytest.mark.django_db
def test_mutation_middleware_context__default():
    validate_called = False

    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input()

        @classmethod
        def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validate_called
            validate_called = True

    input_data = {"name": "foo"}

    with MutationMiddlewareHandler(mutation_type=MyMutationType, info=MockGQLInfo(), input_data=input_data):
        pass

    assert validate_called is True


@pytest.mark.django_db
def test_mutation_middleware_context__custom_middleware():
    pre_called = False
    post_called = False

    class MyMiddleware(MutationMiddleware):
        priority = 101

        def __enter__(self) -> Self:
            nonlocal pre_called, post_called
            pre_called = True
            return self

        def __exit__(self, *args: object, **kwargs: Any) -> bool:
            nonlocal pre_called, post_called
            post_called = True
            return False

    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input()

        @classmethod
        def __middleware__(cls) -> list[type[MutationMiddleware]]:
            return [*super().__middleware__(), MyMiddleware]

    input_data = {"name": "foo"}

    handler = MutationMiddlewareHandler(mutation_type=MyMutationType, info=MockGQLInfo(), input_data=input_data)

    assert pre_called is False
    assert post_called is False

    with handler:
        assert pre_called is True
        assert post_called is False

    assert pre_called is True
    assert post_called is True
