from __future__ import annotations

import os
import time
import traceback
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from django import db
from django.conf import settings

from undine.settings import undine_settings

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

__all__ = [
    "capture_database_queries",
]


@dataclass
class QueryInfo:
    sql: str
    duration_ns: int
    origin: str


@dataclass
class DBQueryData:
    queries: list[QueryInfo]

    @property
    def count(self) -> int:
        return len(self.queries)

    @property
    def log(self) -> str:
        import sqlparse  # type: ignore[import-untyped]  # noqa: PLC0415

        message = "\n" + "-" * 75
        message += f"\n\n>>> Queries: ({len(self.queries)})"

        for index, info in enumerate(self.queries):
            message += "\n\n"
            message += f"{index + 1}) Duration: {info.duration_ns / 1_000_000:.2f} ms"
            message += "\n\n"
            message += "--- Query ".ljust(75, "-")
            message += "\n\n"
            message += sqlparse.format(info.sql, reindent=True)
            message += "\n\n"
            message += "--- Point of origin ".ljust(75, "-")
            message += "\n\n"
            message += info.origin
            message += "\n"
            message += "-" * 75

        return message


def db_query_logger(  # noqa: PLR0917
    execute: Callable[..., Any],
    sql: str,
    params: tuple[Any, ...],
    many: bool,  # noqa: FBT001
    context: dict[str, Any],
    # Added with functools.partial()
    query_data: DBQueryData,
) -> Any:
    """
    A database query logger for capturing executed database queries.
    Used to check that query optimizations work as expected.

    Can also be used as a place to put debugger breakpoint for solving issues.
    """
    # Don't include transaction creation, as we aren't interested in them.
    if sql.startswith(("SAVEPOINT", "RELEASE SAVEPOINT")):
        return execute(sql, params, many, context)

    sql_fmt = sql
    with suppress(TypeError):
        sql_fmt %= params

    info = QueryInfo(sql=sql_fmt, duration_ns=0, origin=get_stack_info())
    query_data.queries.append(info)

    start = time.perf_counter_ns()
    try:
        result = execute(sql, params, many, context)
    finally:
        info.duration_ns = time.perf_counter_ns() - start

    return result


def get_stack_info() -> str:
    if undine_settings.TESTING_CLIENT_FULL_STACKTRACE:
        return "".join(traceback.StackSummary.from_list(traceback.extract_stack()).format())

    venv_path: str | None = os.getenv("VIRTUAL_ENV")
    undine_path = str(Path(__file__).resolve().parent.parent)
    project_path = str(settings.BASE_DIR)

    for frame in reversed(traceback.extract_stack()):
        if frame.filename == __file__:
            continue

        if venv_path is not None and frame.filename.startswith(venv_path):
            continue

        if frame.filename.startswith(undine_path):
            return "".join(traceback.StackSummary.from_list([frame]).format())

        if frame.filename.startswith(project_path):
            return "".join(traceback.StackSummary.from_list([frame]).format())

    return "No info"


@contextmanager
def capture_database_queries() -> Generator[DBQueryData, None, None]:
    """Capture results of what database queries were executed."""
    query_data = DBQueryData(queries=[])
    query_logger = partial(db_query_logger, query_data=query_data)

    with db.connection.execute_wrapper(query_logger):
        yield query_data
