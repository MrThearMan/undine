from __future__ import annotations

from undine.exceptions import GraphQLPaginationArgumentValidationError

__all__ = [
    "validate_after_and_end",
    "validate_first",
    "validate_last",
]


def validate_after_and_end(*, after: str | None, before: str | None) -> None:
    if after is not None and before is not None:
        msg = (
            "Cannot use both 'after' and 'before' arguments together. "
            "Use 'first' and 'after' to paginate forward, or 'last' and 'before' to paginate backward."
        )
        raise GraphQLPaginationArgumentValidationError(msg)


def validate_first(*, first: int | None, last: int | None, before: str | None, page_size: int | None) -> None:
    if first is None:
        return

    if not isinstance(first, int) or first <= 0:
        msg = "Argument 'first' must be a positive integer."
        raise GraphQLPaginationArgumentValidationError(msg)

    if isinstance(page_size, int) and first > page_size:
        msg = f"Requesting first {first} records exceeds the maximum page size of {page_size}."
        raise GraphQLPaginationArgumentValidationError(msg)

    if last is not None:
        msg = (
            "Cannot use both 'first' and 'last' arguments together. "
            "Use 'first' and 'after' to paginate forward, or 'last' and 'before' to paginate backward."
        )
        raise GraphQLPaginationArgumentValidationError(msg)

    if before is not None:
        msg = (
            "Cannot use both 'first' and 'before' arguments together. "
            "Use 'first' and 'after' to paginate forward, or 'last' and 'before' to paginate backward."
        )
        raise GraphQLPaginationArgumentValidationError(msg)


def validate_last(*, last: int | None, after: str | None, page_size: int | None) -> None:
    if last is None:
        return

    if not isinstance(last, int) or last <= 0:
        msg1 = "Argument 'last' must be a positive integer."
        raise GraphQLPaginationArgumentValidationError(msg1)

    if isinstance(page_size, int) and last > page_size:
        msg1 = f"Requesting last {last} records exceeds the maximum page size of {page_size}."
        raise GraphQLPaginationArgumentValidationError(msg1)

    if after is not None:
        msg = (
            "Cannot use both 'last' and 'after' arguments together. "
            "Use 'first' and 'after' to paginate forward, or 'last' and 'before' to paginate backward."
        )
        raise GraphQLPaginationArgumentValidationError(msg)
