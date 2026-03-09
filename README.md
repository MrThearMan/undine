# Undine - GraphQL for Django

[![Coverage Status][coverage-badge]][coverage]
[![GitHub Workflow Status][status-badge]][status]
[![PyPI][pypi-badge]][pypi]
[![GitHub][licence-badge]][licence]
[![GitHub Last Commit][repo-badge]][repo]
[![GitHub Issues][issues-badge]][issues]
[![Downloads][downloads-badge]][pypi]
[![Python Version][version-badge]][pypi]
[![Django Version][django-badge]][pypi]

[coverage-badge]: https://coveralls.io/repos/github/MrThearMan/undine/badge.svg?branch=main
[status-badge]: https://img.shields.io/github/actions/workflow/status/MrThearMan/undine/test.yml?branch=main
[pypi-badge]: https://img.shields.io/pypi/v/undine
[licence-badge]: https://img.shields.io/github/license/MrThearMan/undine
[repo-badge]: https://img.shields.io/github/last-commit/MrThearMan/undine
[issues-badge]: https://img.shields.io/github/issues-raw/MrThearMan/undine
[version-badge]: https://img.shields.io/pypi/pyversions/undine
[downloads-badge]: https://img.shields.io/pypi/dm/undine
[django-badge]: https://img.shields.io/pypi/djversions/undine

[coverage]: https://coveralls.io/github/MrThearMan/undine?branch=main
[status]: https://github.com/MrThearMan/undine/actions/workflows/test.yml
[pypi]: https://pypi.org/project/undine
[licence]: https://github.com/MrThearMan/undine/blob/main/LICENSE
[repo]: https://github.com/MrThearMan/undine/commits/main
[issues]: https://github.com/MrThearMan/undine/issues

```shell
pip install undine
```

---

**Documentation**: [https://mrthearman.github.io/undine/](https://mrthearman.github.io/undine/)

**Source Code**: [https://github.com/MrThearMan/undine/](https://github.com/MrThearMan/undine/)

**Contributing**: [https://mrthearman.github.io/undine/contributing/](https://mrthearman.github.io/undine/contributing/)

---

Undine is a GraphQL library for Django. It's designed to be easy to use and extend
while providing out-of-the-box solutions for many common issues GraphQL developers face.

**Feature highlights:**

- Automatic generation of GraphQL types from Django models
- Automatic query optimization
- Logically composable filtering
- Ordering based on enums
- Single and bulk mutations, including relations
- Hidden and input-only mutation inputs
- Built-in permission and validation hooks
- Support for Relay Global object IDs and Connection pagination
- File uploads based on GraphQL multipart request specification
- Support for asynchronous execution and DataLoaders
- Subscriptions with WebSockets, Server-Sent Events, or Multipart HTTP
- Server-side query caching
- Optional persisted documents support
- Lifecycle hooks for customizing the GraphQL request cycle
- Hiding fields and types from schema (experimental)
- Built-in testing tools

Check out the [Tutorial] to get started.

[Tutorial]: https://mrthearman.github.io/undine/tutorial/

```python
import asyncio
from collections.abc import AsyncIterator
from typing import Any

from undine import (
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    GQLInfo,
    Input,
    MutationType,
    Order,
    OrderSet,
    QueryType,
    RootType,
    create_schema,
)
from undine.exceptions import GraphQLPermissionError, GraphQLValidationError
from undine.relay import Connection, Node
from undine.subscriptions import ModelCreateSubscription

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    name = Filter(lookup="icontains")
    done = Filter()


class TaskOrderSet(OrderSet[Task]):
    id = Order()
    name = Order(null_placement="last")


@Node
@TaskFilterSet
@TaskOrderSet
class TaskType(QueryType[Task], schema_name="Task"):
    pk = Field()
    name = Field()

    @name.permissions
    def name_permissions(self, instance: Task, info: GQLInfo) -> None:
        if not info.context.user.is_authenticated:
            raise GraphQLPermissionError


class TaskCreateMutation(MutationType[Task]):
    name = Input()
    done = Input(default_value=False)

    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if not info.context.user.is_staff:
            msg = "Only staff members can create tasks"
            raise GraphQLPermissionError(msg)

    @classmethod
    def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if len(input_data["name"]) < 3:
            msg = "Task name must be at least 3 characters"
            raise GraphQLValidationError(msg)


class Query(RootType):
    node = Entrypoint(Node)
    task = Entrypoint(TaskType, cache_time=10)
    tasks = Entrypoint(Connection(TaskType))


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
    bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)


class Subscription(RootType):
    task_created = Entrypoint(ModelCreateSubscription(TaskType))

    @Entrypoint
    async def countdown(self, info: GQLInfo) -> AsyncIterator[int]:
        for i in range(10, -1, -1):
            yield i
            await asyncio.sleep(1)


schema = create_schema(query=Query, mutation=Mutation, subscription=Subscription)
```
