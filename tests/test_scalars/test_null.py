import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.null import parse_null


def test_scalar__null__parse__null():
    assert parse_null(None) is None


def test_scalar__null__parse__unsupported_type():
    msg = "Null cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_null(1.2)
