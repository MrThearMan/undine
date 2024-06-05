from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.null import null_scalar


@pytest.mark.parametrize("func", [null_scalar.parse, null_scalar.serialize])
def test_scalar__null__unsupported_type(func) -> None:
    msg = "'Null' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


@pytest.mark.parametrize("func", [null_scalar.parse, null_scalar.serialize])
def test_scalar__null(func) -> None:
    assert func(None) is None
