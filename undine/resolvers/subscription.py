from __future__ import annotations

import dataclasses
from contextlib import aclosing
from typing import TYPE_CHECKING, Any

from graphql import GraphQLError, located_error

from undine.exceptions import GraphQLErrorGroup
from undine.utils.graphql.utils import pre_evaluate_request_user
from undine.utils.reflection import get_root_and_info_params

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from undine import Entrypoint, GQLInfo


__all__ = [
    "EntrypointFunctionSubscription",
    "SubscriptionValueResolver",
]


@dataclasses.dataclass(frozen=True, slots=True)
class SubscriptionValueResolver:  # TODO: Test
    """Resolves a value for a subscription."""

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        return root


@dataclasses.dataclass(frozen=True, slots=True)
class EntrypointFunctionSubscription:  # TODO: Test
    """Subscribes to an `Entrypoint` using the given function."""

    func: Callable[..., AsyncGenerator[Any, None]]
    entrypoint: Entrypoint

    root_param: str | None = dataclasses.field(default=None, init=False)
    info_param: str | None = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        params = get_root_and_info_params(self.func)
        object.__setattr__(self, "root_param", params.root_param)
        object.__setattr__(self, "info_param", params.info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        return self.run_async_gen(root, info, **kwargs)

    async def run_async_gen(self, root: Any, info: GQLInfo, **kwargs: Any) -> AsyncGenerator[Any, None]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info

        gen = self.func(**kwargs)

        async with aclosing(gen):
            try:
                async for result in gen:
                    if isinstance(result, GraphQLError):
                        yield located_error(result, nodes=info.field_nodes, path=info.path.as_list())
                        continue

                    if isinstance(result, GraphQLErrorGroup):
                        yield result.located(path=info.path.as_list())
                        continue

                    if self.entrypoint.permissions_func is not None:
                        self.entrypoint.permissions_func(root, info, result)

                    yield result

            except GraphQLErrorGroup as error:
                raise error.located(path=info.path.as_list()) from error

            except Exception as error:
                raise located_error(error, nodes=info.field_nodes, path=info.path.as_list()) from error
