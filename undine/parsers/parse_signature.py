from __future__ import annotations

import inspect
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FrameType, FunctionType


__all__ = [
    "parse_signature",
]


def parse_signature(func: FunctionType, *, level: int = 0) -> inspect.Signature:
    """
    Parse the signature of a function.

    :param func: The function to parse.
    :param level: How many function calls deep is the code calling this method compared to the parsed function?
    """
    frame: FrameType = sys._getframe(level + 2)  # type: ignore[attr-defined]  # noqa: SLF001

    try:
        return inspect.signature(func, eval_str=True, globals=frame.f_globals, locals=frame.f_locals)
    except NameError as error:
        msg = (
            f"Name '{error.name}' is not defined in module '{func.__module__}'. "
            f"Check if it's inside a `if TYPE_CHECKING` block. The type hint needs to be "
            f"available during runtime so that signature of '{func.__name__}' can be inspected."
        )
        raise RuntimeError(msg) from error
