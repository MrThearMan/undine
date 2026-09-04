from __future__ import annotations

from typing import TYPE_CHECKING

from undine.exceptions import GraphQLMutationInstanceLimitError
from undine.settings import undine_settings

if TYPE_CHECKING:
    from undine.typing import MutationInstanceCounter


__all__ = [
    "add_mutated_instances",
    "check_mutation_instance_limit",
]


def check_mutation_instance_limit(counter: MutationInstanceCounter, amount: int) -> None:
    """
    Check that mutating the given number of instances would stay within `MUTATION_INSTANCE_LIMIT`.

    Use this to reject an oversized request before doing per-instance work. The instances
    themselves are recorded with `add_mutated_instances` once their true number is known.
    """
    total = counter.count + amount
    limit = undine_settings.MUTATION_INSTANCE_LIMIT
    if total > limit:
        raise GraphQLMutationInstanceLimitError(limit=limit, count=total)


def add_mutated_instances(counter: MutationInstanceCounter, amount: int) -> None:
    """Record the given number of mutated instances against `MUTATION_INSTANCE_LIMIT`."""
    check_mutation_instance_limit(counter, amount)
    counter.count += amount
