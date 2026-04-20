from __future__ import annotations

from typing import NamedTuple

import pytest
from django.core.exceptions import ValidationError
from graphql import (
    DirectiveLocation,
    DocumentNode,
    FieldNode,
    FragmentSpreadNode,
    GraphQLError,
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLString,
    GraphQLType,
    GraphQLWrappingType,
    OperationDefinitionNode,
    OperationType,
    Undefined,
    parse,
)
from graphql.language import NameNode
from graphql.pyutils import Path

from example_project.app.models import Task
from tests.helpers import mock_gql_info, parametrize_helper
from undine import Directive
from undine.exceptions import (
    DirectiveLocationError,
    DirectiveRepeatedError,
    GraphQLErrorGroup,
    GraphQLRequestMultipleOperationsNoOperationNameError,
    GraphQLRequestNoOperationError,
    GraphQLRequestOperationNotFoundError,
)
from undine.utils.graphql.utils import (
    check_directives,
    get_arguments,
    get_error_execution_result,
    get_fragment_definitions,
    get_operation_definition,
    get_operation_type,
    get_queried_field_name,
    get_underlying_type,
    graphql_error_path,
    graphql_errors_hook,
    is_atomic_mutation,
    is_connection,
    is_edge,
    is_node_interface,
    is_non_null_default_value,
    is_page_info,
    is_relation_id,
    is_typename_metafield,
    located_validation_error,
    pre_evaluate_request_user,
    should_skip_node,
)


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


def test_get_operation_definition__no_operations() -> None:
    doc = DocumentNode(definitions=[])
    with pytest.raises(GraphQLRequestNoOperationError):
        get_operation_definition(doc, None)


def test_get_operation_definition__single_operation() -> None:
    doc = parse("{ field }")
    result = get_operation_definition(doc, None)
    assert isinstance(result, OperationDefinitionNode)


def test_get_operation_definition__multiple_no_name() -> None:
    doc = parse("query A { field } query B { other }")
    with pytest.raises(GraphQLRequestMultipleOperationsNoOperationNameError):
        get_operation_definition(doc, None)


def test_get_operation_definition__multiple_with_name() -> None:
    doc = parse("query A { field } query B { other }")
    result = get_operation_definition(doc, "B")
    assert result.name.value == "B"


def test_get_operation_definition__name_not_found() -> None:
    doc = parse("query A { field } query B { other }")
    with pytest.raises(GraphQLRequestOperationNotFoundError):
        get_operation_definition(doc, "C")


def test_graphql_error_path__graphql_error_gets_path() -> None:
    info = mock_gql_info()
    msg = "test error"
    with pytest.raises(GraphQLError) as exc_info, graphql_error_path(info):
        raise GraphQLError(msg)
    assert exc_info.value.path is not None


def test_graphql_error_path__error_group_gets_path() -> None:
    info = mock_gql_info()
    error = GraphQLError("group error")
    group = GraphQLErrorGroup(errors=[error])
    with pytest.raises(GraphQLErrorGroup), graphql_error_path(info):
        raise group
    assert error.path is not None


def test_graphql_error_path__with_key() -> None:
    info = mock_gql_info()
    msg = "with key"
    with pytest.raises(GraphQLError) as exc_info, graphql_error_path(info, key="field"):
        raise GraphQLError(msg)
    assert exc_info.value.path is not None


def test_check_directives__none() -> None:
    check_directives(None, location=DirectiveLocation.FIELD)  # should not raise


def test_check_directives__wrong_location() -> None:

    class FieldOnlyDirective(Directive, locations=[DirectiveLocation.FIELD]): ...

    directive = FieldOnlyDirective()
    with pytest.raises(DirectiveLocationError):
        check_directives([directive], location=DirectiveLocation.OBJECT)


def test_check_directives__repeated_non_repeatable() -> None:

    class SingleDirective(Directive, locations=[DirectiveLocation.FIELD]): ...

    d1, d2 = SingleDirective(), SingleDirective()
    with pytest.raises(DirectiveRepeatedError):
        check_directives([d1, d2], location=DirectiveLocation.FIELD)


def test_graphql_errors_hook__empty() -> None:
    assert graphql_errors_hook([]) == []


def test_graphql_errors_hook__graphql_original_error() -> None:
    inner = GraphQLError("inner")
    outer = GraphQLError("outer", original_error=inner)
    result = graphql_errors_hook([outer])
    assert result[0].extensions["status_code"] == 400


def test_graphql_errors_hook__non_graphql_original_error() -> None:
    inner = ValueError("inner")
    outer = GraphQLError("outer", original_error=inner)
    result = graphql_errors_hook([outer])
    assert result[0].extensions["status_code"] == 500


def test_located_validation_error__simple() -> None:
    error = ValidationError("Invalid value", code="invalid")
    result = located_validation_error(error, nodes=[], path=["field"])
    assert isinstance(result, GraphQLErrorGroup)
    errors = list(result.flatten())
    assert len(errors) == 1
    assert "Invalid value" in errors[0].message


def test_located_validation_error__with_field() -> None:
    error = ValidationError({"name": [ValidationError("Too long", code="max_length")]})
    result = located_validation_error(error, nodes=[], path=["parent"])
    errors = list(result.flatten())
    assert any("Too long" in e.message for e in errors)


def test_get_fragment_definitions() -> None:
    doc = parse("fragment F on Task { id } { ...F }")
    result = get_fragment_definitions(doc)
    assert "F" in result


def test_get_operation_type() -> None:
    doc = parse("query { field }")
    result = get_operation_type(doc, None)
    assert result == OperationType.QUERY


def test_get_error_execution_result__list() -> None:
    errors = [GraphQLError("a"), GraphQLError("b")]
    result = get_error_execution_result(errors)
    assert result.data is None
    assert len(result.errors) == 2


def test_get_error_execution_result__error_group() -> None:
    group = GraphQLErrorGroup(errors=[GraphQLError("g")])
    result = get_error_execution_result(group)
    assert result.data is None
    assert len(result.errors) == 1


def test_get_error_execution_result__single() -> None:
    error = GraphQLError("single")
    result = get_error_execution_result(error)
    assert result.data is None
    assert len(result.errors) == 1


def test_is_connection__true() -> None:

    t = GraphQLObjectType(
        "FooConnection",
        fields=lambda: {
            "pageInfo": GraphQLField(GraphQLString),
            "edges": GraphQLField(GraphQLString),
        },
    )
    assert is_connection(t) is True


def test_is_connection__false() -> None:

    t = GraphQLObjectType("Foo", fields={"name": GraphQLField(GraphQLString)})
    assert is_connection(t) is False


def test_is_edge__true() -> None:

    t = GraphQLObjectType(
        "FooEdge",
        fields=lambda: {
            "cursor": GraphQLField(GraphQLString),
            "node": GraphQLField(GraphQLString),
        },
    )
    assert is_edge(t) is True


def test_is_node_interface__true() -> None:

    t = GraphQLInterfaceType("Node", fields={"id": GraphQLField(GraphQLString)})
    assert is_node_interface(t) is True


def test_is_page_info__true() -> None:

    t = GraphQLObjectType(
        "PageInfo",
        fields=lambda: {
            "hasNextPage": GraphQLField(GraphQLString),
            "hasPreviousPage": GraphQLField(GraphQLString),
            "startCursor": GraphQLField(GraphQLString),
            "endCursor": GraphQLField(GraphQLString),
        },
    )
    assert is_page_info(t) is True


def test_is_typename_metafield__true() -> None:
    node = parse("{ __typename }").definitions[0].selection_set.selections[0]
    assert is_typename_metafield(node) is True


def test_is_typename_metafield__false__not_field_node() -> None:
    node = FragmentSpreadNode(name=parse("fragment F on T { id }").definitions[0].name)
    assert is_typename_metafield(node) is False


def test_is_non_null_default_value__true() -> None:
    assert is_non_null_default_value("value") is True


def test_is_non_null_default_value__none() -> None:

    assert is_non_null_default_value(None) is False
    assert is_non_null_default_value(Undefined) is False


def test_is_non_null_default_value__unhashable() -> None:
    assert is_non_null_default_value([1, 2, 3]) is True


def test_is_atomic_mutation__not_mutation() -> None:
    doc = parse("query { field }")
    op = doc.definitions[0]
    assert is_atomic_mutation(op) is False


def test_is_atomic_mutation__mutation_no_atomic() -> None:
    doc = parse("mutation { field }")
    op = doc.definitions[0]
    assert is_atomic_mutation(op) is False


def test_is_atomic_mutation__mutation_with_atomic() -> None:
    doc = parse("mutation @atomic { field }")
    op = doc.definitions[0]
    assert is_atomic_mutation(op) is True


def test_should_skip_node__skip_true() -> None:
    doc = parse("{ field @skip(if: true) }")
    field_node = doc.definitions[0].selection_set.selections[0]
    assert should_skip_node(field_node, {}) is True


def test_should_skip_node__include_false() -> None:
    doc = parse("{ field @include(if: false) }")
    field_node = doc.definitions[0].selection_set.selections[0]
    assert should_skip_node(field_node, {}) is True


def test_should_skip_node__no_directives() -> None:
    doc = parse("{ field }")
    field_node = doc.definitions[0].selection_set.selections[0]
    assert should_skip_node(field_node, {}) is False


def test_graphql_errors_hook__with_traceback(undine_settings) -> None:
    undine_settings.INCLUDE_ERROR_TRACEBACK = True

    try:
        msg = "inner"
        raise ValueError(msg)  #  noqa: TRY301
    except ValueError as exc:
        error = GraphQLError("outer", original_error=exc)
        error.__traceback__ = exc.__traceback__

    result = graphql_errors_hook([error])
    assert "traceback" in result[0].extensions


def test_graphql_error_path__error_already_has_path() -> None:
    info = mock_gql_info()
    error = GraphQLError("test", path=["existing"])
    with pytest.raises(GraphQLError) as exc_info, graphql_error_path(info):
        raise error
    assert exc_info.value.path == ["existing"]


def test_graphql_error_path__error_group_already_has_path() -> None:
    info = mock_gql_info()
    error = GraphQLError("test", path=["existing"])
    group = GraphQLErrorGroup(errors=[error])
    with pytest.raises(GraphQLErrorGroup), graphql_error_path(info):
        raise group
    assert error.path == ["existing"]


def test_graphql_errors_hook__traceback_no_include(undine_settings) -> None:
    undine_settings.INCLUDE_ERROR_TRACEBACK = False

    try:
        msg = "inner"
        raise ValueError(msg)  # noqa: TRY301
    except ValueError as exc:
        error = GraphQLError("outer", original_error=exc)
        error.__traceback__ = exc.__traceback__

    result = graphql_errors_hook([error])
    assert "traceback" not in result[0].extensions


def test_is_relation_id__true() -> None:
    field = Task._meta.get_field("project")
    field_node = parse("{ projectId }").definitions[0].selection_set.selections[0]
    assert is_relation_id(field, field_node) is True


def test_is_relation_id__false__not_fk() -> None:

    field = Task._meta.get_field("name")
    field_node = parse("{ name }").definitions[0].selection_set.selections[0]
    assert is_relation_id(field, field_node) is False


@pytest.mark.asyncio
async def test_pre_evaluate_request_user() -> None:

    class MockUser:
        pass

    class MockContext:
        async def auser(self) -> MockUser:
            return MockUser()

    info = mock_gql_info(context=MockContext())
    await pre_evaluate_request_user(info)
    assert hasattr(info.context, "_cached_user")


def test_get_arguments() -> None:

    field_name = "myField"
    parent_type = GraphQLObjectType(
        "Query",
        fields={
            field_name: GraphQLField(GraphQLString),
        },
    )
    field_node = FieldNode(
        name=NameNode(value=field_name),
        arguments=(),
        directives=(),
        alias=None,
        selection_set=None,
    )
    info = mock_gql_info(field_name=field_name, parent_type=parent_type, field_nodes=[field_node])
    result = get_arguments(info)
    assert result == {}


def test_get_queried_field_name__aliased() -> None:

    info = mock_gql_info(
        field_name="actualField",
        path=Path(prev=None, key="aliasedField", typename="T"),
    )
    result = get_queried_field_name("actualField", info)
    assert result == "aliasedField"
