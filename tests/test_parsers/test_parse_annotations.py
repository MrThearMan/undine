from __future__ import annotations

from typing import Any

import pytest
from django.db.models import QuerySet
from graphql import Undefined

from undine.exceptions import MissingFunctionAnnotationsError, MissingFunctionReturnTypeError, NoFunctionParametersError
from undine.parsers.parse_annotations import parse_first_param_type, parse_parameters, parse_return_annotation
from undine.typing import GQLInfo


def test_parse_parameters() -> None:
    def func(arg: int):
        pass

    params = parse_parameters(func)
    assert len(params) == 1
    assert params[0].name == "arg"
    assert params[0].annotation == int
    assert params[0].default_value == Undefined


def test_parse_parameters__missing_annotations() -> None:
    def func(arg):
        pass

    with pytest.raises(MissingFunctionAnnotationsError):
        parse_parameters(func)


def test_parse_parameters__dont_parse_self() -> None:
    def func(self, arg: str):
        pass

    params = parse_parameters(func)
    assert len(params) == 1
    assert params[0].name == "arg"
    assert params[0].annotation == str
    assert params[0].default_value == Undefined


def test_parse_parameters__dont_parse_cls() -> None:
    def func(cls, arg: str):
        pass

    params = parse_parameters(func)
    assert len(params) == 1
    assert params[0].name == "arg"
    assert params[0].annotation == str
    assert params[0].default_value == Undefined


def test_parse_parameters__dont_parse_gql_info() -> None:
    def func(info: GQLInfo, arg: str):
        pass

    params = parse_parameters(func)
    assert len(params) == 1
    assert params[0].name == "arg"
    assert params[0].annotation == str
    assert params[0].default_value == Undefined


def test_parse_parameters__dont_parse_queryset() -> None:
    def func(qs: QuerySet, arg: str):
        pass

    params = parse_parameters(func)
    assert len(params) == 1
    assert params[0].name == "arg"
    assert params[0].annotation == str
    assert params[0].default_value == Undefined


def test_parse_parameters__default_value() -> None:
    def func(arg: int = 10):
        pass

    params = parse_parameters(func)
    assert len(params) == 1
    assert params[0].name == "arg"
    assert params[0].annotation == int
    assert params[0].default_value == 10


def test_parse_parameters__ignore_args_and_kwargs() -> None:
    def func(arg: Any, *args, **kwargs):
        pass

    params = parse_parameters(func)
    assert len(params) == 1
    assert params[0].name == "arg"
    assert params[0].annotation == Any
    assert params[0].default_value == Undefined


def test_parse_parameters__no_parameters() -> None:
    def func() -> None:
        pass

    params = parse_parameters(func)
    assert len(params) == 0


def test_parse_first_param_type() -> None:
    def func(arg: int, arg2: str):
        pass

    ann = parse_first_param_type(func)
    assert ann == int


def test_parse_first_param_type__no_parameters() -> None:
    def func() -> None:
        pass

    with pytest.raises(NoFunctionParametersError):
        parse_first_param_type(func)


def test_parse_return_annotation() -> None:
    def func() -> int:
        pass

    ann = parse_return_annotation(func)
    assert ann == int


def test_parse_return_annotation__missing_annotations() -> None:
    def func():
        pass

    with pytest.raises(MissingFunctionReturnTypeError):
        parse_return_annotation(func)
