from __future__ import annotations

import itertools
from copy import deepcopy
from typing import Any

import pytest
from django.db.models import Model

from example_project.app.models import Comment, Person, Project, ServiceRequest, Task, TaskTypeChoices, Team
from tests.factories import UserFactory
from tests.helpers import MockGQLInfo, MockRequest
from undine import Input, MutationType
from undine.middleware.mutation import (
    AfterMutationMiddleware,
    InputDataModificationMiddleware,
    InputDataValidationMiddleware,
    InputOnlyDataRemovalMiddleware,
    MutationMiddleware,
    MutationMiddlewareHandler,
    MutationPermissionCheckMiddleware,
)
from undine.typing import GQLInfo, JsonObject, MutationResult


def test_middleware__input_data_modification_middleware():
    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input(hidden=True, default_value="foo")

        @Input
        def current_user_id(self: Input, info: GQLInfo) -> int | None:
            return info.context.user.id

    middleware = InputDataModificationMiddleware(
        mutation_type=MyMutationType,
        info=MockGQLInfo(context=MockRequest(user=UserFactory.build(id=1))),
        input_data={},
    )

    middleware.before()

    assert middleware.input_data == {
        "name": "foo",
        "current_user_id": 1,
    }

    middleware.after(None)

    assert middleware.input_data == {
        "name": "foo",
        "current_user_id": 1,
    }


def test_middleware__mutation_permission_check_middleware():
    counter = itertools.count(1)
    pemissions_called = -1
    name_permissions_called = -1
    type_permissions_called = -1

    class TaskCreateMutation(MutationType, model=Task):
        name = Input()
        type = Input()

        @name.permissions
        def name_permissions(self: Input, info: GQLInfo, value: str) -> None:
            nonlocal name_permissions_called
            name_permissions_called = next(counter)

        @type.permissions
        def type_permissions(self: Input, info: GQLInfo, value: str) -> None:
            nonlocal type_permissions_called
            type_permissions_called = next(counter)

        @classmethod
        def __permissions__(cls, info: GQLInfo, input_data: JsonObject, **kwargs: Any) -> None:
            nonlocal pemissions_called
            pemissions_called = next(counter)

    middleware = MutationPermissionCheckMiddleware(
        mutation_type=TaskCreateMutation,
        info=MockGQLInfo(),
        input_data={"name": "foo"},
    )

    middleware.before()

    assert name_permissions_called == 1
    assert pemissions_called == 2

    assert type_permissions_called == -1  # Not in input data.


def test_middleware__input_data_validation_middleware():
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
        mutation_type=MyMutationType,
        info=MockGQLInfo(),
        input_data=deepcopy(input_data),
    )

    middleware.before()

    assert validator_1_called == 1
    assert validator_2_called == 2
    assert validate_called == 3


def test_middleware__after_mutation_middleware():
    post_handler_called = False

    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input()

        @classmethod
        def __after__(cls, info: GQLInfo, value: Model) -> None:
            nonlocal post_handler_called
            post_handler_called = True

    input_data = {
        "name": "foo",
    }

    middleware = AfterMutationMiddleware(
        mutation_type=MyMutationType,
        info=MockGQLInfo(),
        input_data=deepcopy(input_data),
    )

    middleware.before()

    assert post_handler_called is False

    middleware.after(None)

    assert post_handler_called is True


def test_middleware__input_only_data_removal_middleware():
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
        mutation_type=MyMutationType,
        info=MockGQLInfo(),
        input_data=deepcopy(input_data),
    )

    middleware.before()

    assert middleware.input_data == {
        "type": TaskTypeChoices.STORY.value,
        "created_at": "2022-01-01T00:00:00",
    }

    middleware.after(None)

    assert middleware.input_data == input_data


def test_middleware__input_only_data_removal_middleware__nested():
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
        mutation_type=MyTaskType,
        info=MockGQLInfo(),
        input_data=deepcopy(input_data),
    )

    middleware.before()

    assert middleware.input_data == {
        "type": TaskTypeChoices.STORY.value,
        "project": {"pk": 1, "comments": [{}]},
        "request": {},
        "assignees": [{"name": "Test user"}],
    }

    middleware.after(None)

    assert middleware.input_data == input_data


@pytest.mark.django_db
def test_middleware__mutation_middleware_handler__default():
    class MyMutationType(MutationType, model=Task, auto=False):
        name = Input()

    input_data = {"name": "foo"}

    middlewares = MutationMiddlewareHandler(MockGQLInfo(), input_data, mutation_type=MyMutationType)

    @middlewares.wrap
    def resolver(*args, **kwargs):
        pass

    resolver()


@pytest.mark.django_db
def test_middleware__mutation_middleware_handler__custom_middleware():
    before_called = False
    after_called = False

    class MyMiddleware(MutationMiddleware):
        priority = 101

        def before(self) -> None:
            nonlocal before_called
            before_called = True

        def after(self, value: MutationResult) -> None:
            nonlocal after_called
            after_called = True

    class TaskMutation(MutationType, model=Task, auto=False):
        name = Input()

        @classmethod
        def __middleware__(cls) -> list[type[MutationMiddleware]]:
            return [*super().__middleware__(), MyMiddleware]

    input_data = {"name": "foo"}

    middlewares = MutationMiddlewareHandler(MockGQLInfo(), input_data, mutation_type=TaskMutation)

    assert before_called is False
    assert after_called is False

    @middlewares.wrap
    def resolver(*args, **kwargs):
        pass

    resolver()

    assert before_called is True
    assert after_called is True
