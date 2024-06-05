from __future__ import annotations

from typing import NamedTuple

import pytest
from graphql import GraphQLList, GraphQLNonNull, GraphQLString, GraphQLType, GraphQLWrappingType

from tests.helpers import parametrize_helper
from undine.utils.graphql.utils import get_underlying_type


class Params(NamedTuple):
    input_type: GraphQLWrappingType
    output_type: GraphQLType


@pytest.mark.parametrize(
    **parametrize_helper({
        "list": Params(
            input_type=GraphQLList(GraphQLString),
            output_type=GraphQLString,
        ),
        "non_null": Params(
            input_type=GraphQLNonNull(GraphQLString),
            output_type=GraphQLString,
        ),
        "non_null_list": Params(
            input_type=GraphQLNonNull(GraphQLList(GraphQLString)),
            output_type=GraphQLString,
        ),
        "non_null_list_of_non_null": Params(
            input_type=GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString))),
            output_type=GraphQLString,
        ),
    })
)
def test_graphql_utils__get_underlying_type(input_type, output_type):
    assert get_underlying_type(input_type) == output_type
