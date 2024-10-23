import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.null import parse_null, serialize


@pytest.mark.parametrize("func", [parse_null, serialize])
def test_scalar__null__parse__null(func):
    assert func(None) is None


@pytest.mark.parametrize("func", [parse_null, serialize])
def test_scalar__null__parse__unsupported_type(func):
    msg = "Null cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1.2)
