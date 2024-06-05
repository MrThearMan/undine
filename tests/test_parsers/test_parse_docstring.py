from __future__ import annotations

import pytest

from undine.errors.exceptions import InvalidParserError
from undine.parsers.parse_docstring import (
    PlainDocstringParser,
    PreProcessingDocstringParser,
    RSTDocstringParser,
    parse_class_variable_docstrings,
)


def test_parse_docstring__rst__parse_body():
    docstring = """
    Body.

    :param foo: bar
    :returns: fizzbuzz
    """

    assert RSTDocstringParser.parse_body(docstring) == "Body."


def test_parse_docstring__rst__parse_body__no_docstring():
    assert RSTDocstringParser.parse_body("") == ""


def test_parse_docstring__rst__parse_arg_descriptions():
    docstring = """
    Body.

    :param foo: bar
    :param x: y
    :returns: fizzbuzz
    """

    assert RSTDocstringParser.parse_arg_descriptions(docstring) == {"foo": "bar", "x": "y"}


def test_parse_docstring__rst__parse_arg_descriptions__no_docstring():
    assert RSTDocstringParser.parse_arg_descriptions("") == {}


def test_parse_docstring__rst__parse_return_description():
    docstring = """
    Body.

    :param foo: bar
    :returns: fizzbuzz
    """

    assert RSTDocstringParser.parse_return_description(docstring) == "fizzbuzz"


def test_parse_docstring__rst__parse_return_description__no_docstring():
    assert RSTDocstringParser.parse_return_description("") == ""


def test_parse_docstring__rst__parse_raise_descriptions():
    docstring = """
    Body.

    :param foo: bar
    :returns: fizzbuzz
    :raises TypeError: nothing
    """

    assert RSTDocstringParser.parse_raise_descriptions(docstring) == {"TypeError": "nothing"}


def test_parse_docstring__rst__parse_raise_descriptions__no_docstring():
    assert RSTDocstringParser.parse_raise_descriptions("") == {}


def test_parse_docstring__rst__parse_deprecations():
    docstring = """
    Body.

    :param foo: bar
    :deprecated foo: because
    """

    assert RSTDocstringParser.parse_deprecations(docstring) == {"foo": "because"}


def test_parse_docstring__rst__parse_deprecations__no_docstring():
    assert RSTDocstringParser.parse_deprecations("") == {}


def test_parse_docstring__plain():
    docstring = """
    Body.
    """

    assert PlainDocstringParser.parse_body(docstring) == "Body."
    assert PlainDocstringParser.parse_arg_descriptions(docstring) == {}
    assert PlainDocstringParser.parse_return_description(docstring) == ""
    assert PlainDocstringParser.parse_raise_descriptions(docstring) == {}
    assert PlainDocstringParser.parse_deprecations(docstring) == {}


def test_pre_processing_docstring_parser__not_a_valid_parser():
    class MyParser: ...

    with pytest.raises(InvalidParserError):
        PreProcessingDocstringParser(parser_impl=MyParser)  # type: ignore[arg-type]


def test_pre_processing_docstring_parser__none():
    parser = PreProcessingDocstringParser(parser_impl=PlainDocstringParser)

    assert parser.parse_body(None) is None
    assert parser.parse_arg_descriptions(None) == {}
    assert parser.parse_return_description(None) is None
    assert parser.parse_raise_descriptions(None) == {}
    assert parser.parse_deprecations(None) == {}


def test_pre_processing_docstring_parser__strip():
    parser = PreProcessingDocstringParser(parser_impl=PlainDocstringParser)

    assert parser.parse_body(" foo ") == "foo"
    assert parser.parse_arg_descriptions(" foo ") == {}
    assert parser.parse_return_description(" foo ") == ""
    assert parser.parse_raise_descriptions(" foo ") == {}
    assert parser.parse_deprecations(" foo ") == {}


def test_parse_class_variable_docstrings():
    class Foo:
        bar: int = 1
        """Description."""

        baz: int = 2
        """
        Another
        description.
        """

        buzz: int = 3

    assert parse_class_variable_docstrings(Foo) == {"bar": "Description.", "baz": "Another\ndescription."}
