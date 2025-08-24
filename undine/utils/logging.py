from __future__ import annotations

import io
import logging
from traceback import print_tb
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from types import TracebackType

__all__ = [
    "log_traceback",
    "logger",
]


logger = logging.getLogger("undine")


def log_traceback(tb: TracebackType, *, level: Literal[0, 10, 20, 30, 40, 50] = logging.DEBUG) -> None:
    buf = io.StringIO()
    print_tb(tb, file=buf)
    buf.seek(0)
    msg = buf.read()
    logger.log(level, msg)
