from __future__ import annotations

import datetime
import random
from typing import TYPE_CHECKING, Any

from graphql import GraphQLField, GraphQLNonNull, GraphQLString

from undine import Field, QueryType
from undine.scalars import GraphQLDateTime

from .models import Task

if TYPE_CHECKING:
    from undine import GQLInfo


class TimestampedError(Exception):
    def __init__(self, message: str, /, *, timestamp: datetime.datetime) -> None:
        self.timestamp = timestamp
        super().__init__(message)

    @staticmethod
    def graphql_fields() -> dict[str, GraphQLField]:
        return {
            "message": GraphQLField(GraphQLNonNull(GraphQLString)),
            "timestamp": GraphQLField(GraphQLNonNull(GraphQLDateTime)),
        }

    @staticmethod
    def graphql_resolve(root: TimestampedError, info: GQLInfo, **kwargs: Any) -> dict[str, Any]:
        return {
            "message": str(root),
            "timestamp": root.timestamp,
        }


class TaskType(QueryType[Task]):
    @Field(errors=[TimestampedError])
    def example(self) -> str:
        if random.random() > 0.5:
            msg = "Failed"
            raise TimestampedError(msg, timestamp=datetime.datetime.now(tz=datetime.UTC))
        return "OK"
