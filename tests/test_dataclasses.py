from __future__ import annotations

import dataclasses
from typing import NamedTuple, TypedDict

from undine.dataclasses import Calculated, Parameter


def test_dataclass__calculated__typed_dict():
    class Arguments(TypedDict, total=False):
        value: int
        """Description"""

    calculated = Calculated(Arguments, return_annotation=int | None)

    assert calculated.parameters == (
        Parameter(
            name="value",
            annotation=int,
            docstring="Description",
        ),
    )
    assert calculated.return_annotation == int | None


def test_dataclass__calculated__named_tuple():
    class Arguments(NamedTuple):
        value: int | None = 1
        """Description"""

    calculated = Calculated(Arguments, return_annotation=str)

    assert calculated.parameters == (
        Parameter(
            name="value",
            annotation=int | None,
            default_value=1,
            docstring="Description",
        ),
    )
    assert calculated.return_annotation == str


def test_dataclass__calculated__dataclass():
    @dataclasses.dataclass
    class Arguments:
        value: int | None = 1
        """Description"""

    calculated = Calculated(Arguments, return_annotation=str)

    assert calculated.parameters == (
        Parameter(
            name="value",
            annotation=int | None,
            default_value=1,
            docstring="Description",
        ),
    )
    assert calculated.return_annotation == str
