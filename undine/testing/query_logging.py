from __future__ import annotations

import time
import traceback
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Callable, Generator

import sqlparse
from django import db

from undine.utils.logging import undine_logger

__all__ = [
    "capture_database_queries",
]


THIS_FILE = str(Path(__file__).resolve())
BASE_PATH = str(Path(__file__).resolve().parent.parent.parent)


@dataclass
class QueryInfo:
    sql: str
    duration_ns: int
    origin: str


@dataclass
class QueryData:
    query_info: list[QueryInfo]

    @property
    def count(self) -> int:
        return len(self.query_info)

    @property
    def log(self) -> str:
        message = "\n" + "-" * 75
        message += f"\n\n>>> Queries: ({len(self.query_info)})"

        for index, info in enumerate(self.query_info):
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


def db_query_logger(
    execute: Callable[..., Any],
    sql: str,
    params: tuple[Any, ...],
    many: bool,  # noqa: FBT001
    context: dict[str, Any],
    # Added with functools.partial()
    query_data: QueryData,
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
    query_data.query_info.append(info)

    start = time.perf_counter_ns()
    try:
        result = execute(sql, params, many, context)
    finally:
        info.duration_ns = time.perf_counter_ns() - start

    return result


def get_stack_info() -> str:
    for frame in reversed(traceback.extract_stack()):
        if frame.filename == THIS_FILE:
            continue
        is_own_file = frame.filename.startswith(BASE_PATH)
        if is_own_file:
            return "".join(traceback.StackSummary.from_list([frame]).format())

    return "No info"


@contextmanager
def capture_database_queries(*, log: bool = True) -> Generator[QueryData, None, None]:
    """Capture results of what database queries were executed."""
    query_data = QueryData(query_info=[])
    query_logger = partial(db_query_logger, query_data=query_data)

    try:
        with db.connection.execute_wrapper(query_logger):
            yield query_data
    finally:
        if log:
            undine_logger.info(query_data.log)
