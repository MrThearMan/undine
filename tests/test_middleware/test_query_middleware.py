from django.db.models import Model

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo
from undine import Field, QueryType
from undine.middleware.query import QueryMiddleware, QueryMiddlewareHandler, QueryPermissionCheckMiddleware
from undine.typing import GQLInfo, QueryResult


def test_middleware__query_permission_check_middleware__field():
    field_pemissions_called = False

    class TaskType(QueryType, model=Task, auto=False):
        name = Field()

        @name.permissions
        def name_permissions(self: Field, info: GQLInfo, instance: Model) -> None:
            nonlocal field_pemissions_called
            field_pemissions_called = True

    task = TaskFactory.build(name="foo")

    middleware = QueryPermissionCheckMiddleware(root=None, info=MockGQLInfo(), query_type=TaskType)

    middleware.before()
    assert field_pemissions_called is False

    middleware.root = None
    middleware.field = TaskType.name

    middleware.before()
    assert field_pemissions_called is False

    middleware.root = task
    middleware.field = None

    middleware.before()
    assert field_pemissions_called is False

    middleware.root = task
    middleware.field = TaskType.name

    middleware.before()
    assert field_pemissions_called is True


def test_middleware__query_permission_check_middleware__query_type__single():
    pemissions_single_called = False

    class TaskType(QueryType, model=Task, auto=False):
        name = Field()

        @classmethod
        def __permissions_single__(cls, instance: Task, info: GQLInfo) -> None:
            nonlocal pemissions_single_called
            pemissions_single_called = True

    task = TaskFactory.build(name="foo")

    middleware = QueryPermissionCheckMiddleware(root=None, info=MockGQLInfo(), query_type=TaskType)

    middleware.after(value=None)
    assert pemissions_single_called is False

    middleware.after(value=task)
    assert pemissions_single_called is True

    pemissions_single_called = False
    middleware.field = TaskType.name

    middleware.after(value=task)
    assert pemissions_single_called is True

    pemissions_single_called = False
    TaskType.name.skip_query_type_perms = True

    middleware.after(value=task)
    assert pemissions_single_called is False


def test_middleware__query_permission_check_middleware__query_type__many():
    pemissions_many_called = False

    class TaskType(QueryType, model=Task, auto=False):
        name = Field()

        @classmethod
        def __permissions_many__(cls, instance: Task, info: GQLInfo) -> None:
            nonlocal pemissions_many_called
            pemissions_many_called = True

    task = TaskFactory.build(name="foo")

    middleware = QueryPermissionCheckMiddleware(root=task, info=MockGQLInfo(), query_type=TaskType, many=True)

    middleware.after(value=None)
    assert pemissions_many_called is False

    middleware.after(value=[task])
    assert pemissions_many_called is True

    pemissions_many_called = False
    middleware.field = TaskType.name

    middleware.after(value=[task])
    assert pemissions_many_called is True

    pemissions_many_called = False
    TaskType.name.skip_query_type_perms = True

    middleware.after(value=[task])
    assert pemissions_many_called is False


def test_middleware__query_middleware_handler():
    class TaskType(QueryType, model=Task, auto=False):
        name = Field()

    middlewares = QueryMiddlewareHandler(None, MockGQLInfo(), TaskType)

    @middlewares.wrap
    def resolver(*args, **kwargs):
        pass

    resolver()


def test_middleware__query_middleware_handler__custom_middleware():
    before_called = False
    after_called = False

    class MyMiddleware(QueryMiddleware):
        priority = 101

        def before(self) -> None:
            nonlocal before_called
            before_called = True

        def after(self, value: QueryResult) -> None:
            nonlocal after_called
            after_called = True

    class TaskType(QueryType, model=Task, auto=False):
        name = Field()

        @classmethod
        def __middleware__(cls) -> list[type[QueryMiddleware]]:
            return [*super().__middleware__(), MyMiddleware]

    middlewares = QueryMiddlewareHandler(None, MockGQLInfo(), TaskType)

    assert before_called is False
    assert after_called is False

    @middlewares.wrap
    def resolver(*args, **kwargs):
        pass

    resolver()

    assert before_called is True
    assert after_called is True
