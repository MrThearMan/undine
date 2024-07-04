from undine.parsers.parse_docstring import PlainDocstringParser, RSTDocstringParser


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


def test_parse_docstring__plain__parse_body():
    docstring = """
    Body.
    """

    assert PlainDocstringParser.parse_body(docstring) == "Body."
