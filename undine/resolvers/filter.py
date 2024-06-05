from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from django.db.models import Q

from undine.utils.reflection import get_root_and_info_params

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FunctionType

    from undine.typing import GQLInfo

__all__ = [
    "FilterFunctionResolver",
    "FilterModelFieldResolver",
]


@dataclasses.dataclass(frozen=True, slots=True)
class FilterFunctionResolver:
    """Resolves a `FilterSet` field function."""

    func: FunctionType | Callable[..., Any] = dataclasses.field(kw_only=True)
    root_param: str | None = dataclasses.field(default=None, init=False)
    info_param: str | None = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        params = get_root_and_info_params(self.func)
        object.__setattr__(self, "root_param", params.root_param)
        object.__setattr__(self, "info_param", params.info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Q:
        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info
        return self.func(**kwargs)


@dataclasses.dataclass(frozen=True, slots=True)
class FilterModelFieldResolver:
    """Resolves a filter to a model field lookup."""

    lookup: str

    def __call__(self, root: Any, info: GQLInfo, *, value: Any) -> Q:
        return Q(**{self.lookup: value})


@dataclasses.dataclass(frozen=True, slots=True)
class FilterQExpressionResolver:
    """Resolves a filter using a Q expression."""

    q_expression: Q

    def __call__(self, root: Any, info: GQLInfo, *, value: bool) -> Q:
        return self.q_expression if value else ~self.q_expression
