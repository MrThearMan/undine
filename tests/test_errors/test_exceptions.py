from undine import Entrypoint
from undine.errors.exceptions import ErrorMessageFormatter

formatter = ErrorMessageFormatter()


def test_error_formatter__dotpath():
    value = formatter.format_field(Entrypoint, format_spec="dotpath")
    assert value == "undine.schema.Entrypoint"


def test_error_formatter__module():
    value = formatter.format_field(Entrypoint, format_spec="module")
    assert value == "undine.schema"


def test_error_formatter__name():
    value = formatter.format_field(Entrypoint, format_spec="name")
    assert value == "Entrypoint"


def test_error_formatter__qualname():
    value = formatter.format_field(Entrypoint, format_spec="qualname")
    assert value == "Entrypoint"


def test_error_formatter__comma_sep_or():
    value = formatter.format_field(["foo", "bar", "baz"], format_spec="comma_sep_or")
    assert value == "'foo', 'bar' or 'baz'"


def test_error_formatter__comma_sep_and():
    value = formatter.format_field(["foo", "bar", "baz"], format_spec="comma_sep_and")
    assert value == "'foo', 'bar' and 'baz'"
