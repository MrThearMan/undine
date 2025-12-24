from collections.abc import Generator
from time import perf_counter_ns
from typing import Any

from graphql import GraphQLFieldResolver

from undine import GQLInfo
from undine.hooks import LifecycleHook, LifecycleHookContext


class TimingHook(LifecycleHook):
    """Time the execution of each step of the GraphQL operation."""

    def __init__(self, context: LifecycleHookContext) -> None:
        super().__init__(context)

        self.parse_timing: float | None = None
        self.validation_timing: float | None = None
        self.execution_timing: float | None = None
        self.resolver_timings: dict[str, float] = {}

    def on_operation(self) -> Generator[None, None, None]:
        start = perf_counter_ns()
        try:
            yield
        finally:
            end = perf_counter_ns()

            timings = {
                "operation": end - start,
                "parse": self.parse_timing,
                "validation": self.validation_timing,
                "execution": self.execution_timing,
                "resolvers": self.resolver_timings,
            }

            if self.context.result is not None:
                self.context.result.extensions["timings"] = timings

    def on_parse(self) -> Generator[None, None, None]:
        start = perf_counter_ns()
        try:
            yield
        finally:
            self.parse_timing = perf_counter_ns() - start

    def on_validation(self) -> Generator[None, None, None]:
        start = perf_counter_ns()
        try:
            yield
        finally:
            self.validation_timing = perf_counter_ns() - start

    def on_execution(self) -> Generator[None, None, None]:
        start = perf_counter_ns()
        try:
            yield
        finally:
            self.execution_timing = perf_counter_ns() - start

    def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        start = perf_counter_ns()
        try:
            return resolver(root, info, **kwargs)
        finally:
            key = ".".join(str(key) for key in info.path.as_list())
            self.resolver_timings[key] = perf_counter_ns() - start
