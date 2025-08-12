from __future__ import annotations

from inspect import cleandoc

import pytest
from graphql import DirectiveLocation, GraphQLArgument, GraphQLDirective, GraphQLInt, GraphQLNonNull, Undefined

from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError
from undine.utils.graphql.type_registry import GRAPHQL_REGISTRY


def test_directive__attributes(undine_settings) -> None:
    undine_settings.ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS = True

    class ValueDirective(
        Directive,
        locations=[DirectiveLocation.FIELD_DEFINITION],
        is_repeatable=True,
        schema_name="value",
        extensions={"foo:": "bar"},
    ):
        """Description."""

        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))
        """Argument description."""

    assert ValueDirective.__locations__ == [DirectiveLocation.FIELD_DEFINITION]
    assert ValueDirective.__arguments__ == {"value": ValueDirective.value}
    assert ValueDirective.__is_repeatable__ is True
    assert ValueDirective.__schema_name__ == "value"
    assert ValueDirective.__extensions__ == {"undine_directive": ValueDirective, "foo:": "bar"}
    assert ValueDirective.__attribute_docstrings__ == {"value": "Argument description."}

    assert "value" in GRAPHQL_REGISTRY
    assert isinstance(GRAPHQL_REGISTRY["value"], GraphQLDirective)


def test_directive__str() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        """Description."""

        value = DirectiveArgument(GraphQLNonNull(GraphQLInt), description="Argument description.")

    assert str(ValueDirective) == cleandoc(
        '''
        """Description."""
        directive @value(
          """Argument description."""
          value: Int!
        ) on FIELD_DEFINITION
        '''
    )


def test_directive__as_graphql_directive() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        """Description."""

        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    directive = ValueDirective.__directive__()

    assert isinstance(directive, GraphQLDirective)

    assert directive.name == "value"
    assert directive.locations == (DirectiveLocation.FIELD_DEFINITION,)
    assert directive.args == {"value": ValueDirective.value.as_graphql_argument()}
    assert directive.is_repeatable is False
    assert directive.description == "Description."
    assert directive.extensions == {"undine_directive": ValueDirective}


def test_directive__argument__repr() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert repr(ValueDirective.value) == (
        "<undine.directives.DirectiveArgument(input_type=<GraphQLNonNull <GraphQLScalarType 'Int'>>)>"
    )


def test_directive__argument__str() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert str(ValueDirective.value) == "value: Int!"


def test_directive__argument__attributes() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert ValueDirective.value.input_type == GraphQLNonNull(GraphQLInt)
    assert ValueDirective.value.description is None
    assert ValueDirective.value.default_value is Undefined
    assert ValueDirective.value.deprecation_reason is None
    assert ValueDirective.value.schema_name == "value"
    assert ValueDirective.value.directives == []
    assert ValueDirective.value.extensions == {"undine_directive_argument": ValueDirective.value}

    assert ValueDirective.value.directive == ValueDirective
    assert ValueDirective.value.name == "value"


def test_directive__argument__description() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt), description="Description.")

    assert ValueDirective.value.description == "Description."


def test_directive__argument__description__attribute(undine_settings) -> None:
    undine_settings.ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS = True

    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))
        """Description."""

    assert ValueDirective.value.description == "Description."


def test_directive__argument__schema_name() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert ValueDirective.value.schema_name == "value"

    assert str(ValueDirective.value) == "value: Int!"


def test_directive__argument__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ARGUMENT_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    directives: list[Directive] = [ValueDirective(value=1)]

    class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="my"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt), directives=directives)

    assert MyDirective.value.directives == directives

    assert str(MyDirective.value) == "value: Int! @value(value: 1)"


def test_directive__argument__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="my"):
            value = DirectiveArgument(GraphQLNonNull(GraphQLInt), directives=directives)


def test_directive__argument__as_graphql_argument() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    argument = ValueDirective.value.as_graphql_argument()

    assert isinstance(argument, GraphQLArgument)

    assert argument.type == GraphQLNonNull(GraphQLInt)
    assert argument.default_value is Undefined
    assert argument.description is None
    assert argument.out_name == "value"
    assert argument.extensions == {"undine_directive_argument": ValueDirective.value}
