from __future__ import annotations

import pytest
from django.db.models import Value
from graphql import DirectiveLocation, GraphQLArgument, GraphQLInt, GraphQLNonNull, Undefined

from tests.helpers import mock_gql_info
from undine import Calculation, CalculationArgument, DjangoExpression, GQLInfo
from undine.directives import Directive
from undine.exceptions import GraphQLMissingCalculationArgumentError, GraphQLUnexpectedCalculationArgumentError


def test_calculation__definition(undine_settings) -> None:
    undine_settings.ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS = True

    class ExampleCalculation(Calculation[int]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert ExampleCalculation.__returns__ == int
    assert ExampleCalculation.__arguments__ == {"value": ExampleCalculation.value}
    assert ExampleCalculation.__attribute_docstrings__ == {"value": "Value description."}


def test_calculation__definition__argument() -> None:
    class ExampleCalculation(Calculation[int]):
        """Description."""

        value = CalculationArgument(int, description="Value description.")

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert ExampleCalculation.value.default_value is Undefined
    assert ExampleCalculation.value.description == "Value description."
    assert ExampleCalculation.value.deprecation_reason is None
    assert ExampleCalculation.value.schema_name == "value"
    assert ExampleCalculation.value.directives == []
    assert ExampleCalculation.value.extensions == {"undine_calculation_argument": ExampleCalculation.value}


def test_calculation__definition__argument__repr() -> None:
    class ExampleCalculation(Calculation[int]):
        """Description."""

        value = CalculationArgument(int, description="Value description.")

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert repr(ExampleCalculation.value) == "<undine.calculation.CalculationArgument(ref=<class 'int'>)>"


def test_calculation__definition__argument__str() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert str(ExampleCalculation.value) == "value: Int!"


def test_calculation__definition__argument__graphql_argument() -> None:
    class ExampleCalculation(Calculation[int]):
        """Description."""

        value = CalculationArgument(int, description="Value description.")

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    arg = ExampleCalculation.value.as_graphql_argument()
    assert isinstance(arg, GraphQLArgument)
    assert arg.type == GraphQLNonNull(GraphQLInt)


def test_calculation__definition__argument__deprecation_reason() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int | None, deprecation_reason="Deprecated argument.")

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert ExampleCalculation.value.deprecation_reason == "Deprecated argument."


def test_calculation__definition__argument__default_value() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int, default_value=1)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert ExampleCalculation.value.default_value == 1

    arg = ExampleCalculation.value.as_graphql_argument()
    assert arg.default_value == 1


def test_calculation__definition__argument__schema_name() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int, schema_name="val")

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert ExampleCalculation.value.schema_name == "val"

    assert str(ExampleCalculation.value) == "val: Int!"

    arg = ExampleCalculation.value.as_graphql_argument()
    assert arg.out_name == "value"


def test_calculation__definition__argument__directives() -> None:
    class ArgDirective(Directive, locations=[DirectiveLocation.ARGUMENT_DEFINITION], schema_name="arg"): ...

    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int, directives=[ArgDirective()])

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert ExampleCalculation.value.directives == [ArgDirective()]

    assert str(ExampleCalculation.value) == "value: Int! @arg"


def test_calculation__definition__argument__extensions() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int, extensions={"foo": "bar"})

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    extensions = {
        "foo": "bar",
        "undine_calculation_argument": ExampleCalculation.value,
    }

    assert ExampleCalculation.value.extensions == extensions

    arg = ExampleCalculation.value.as_graphql_argument()
    assert arg.extensions == extensions


def test_calculation__instance() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    calc = ExampleCalculation("foo", value=1)

    assert calc.__field_name__ == "foo"
    assert calc.__parameters__ == {"value": 1}

    assert calc.value == 1

    info = mock_gql_info()
    assert calc(info) == Value(1)


def test_calculation__instance__missing_argument() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    with pytest.raises(GraphQLMissingCalculationArgumentError):
        ExampleCalculation("foo")


def test_calculation__instance__missing_argument__default_value() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int, default_value=1)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    calc = ExampleCalculation("foo")

    assert calc.__parameters__ == {"value": 1}
    assert calc.value == 1


def test_calculation__instance__extra_argument() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    with pytest.raises(GraphQLUnexpectedCalculationArgumentError):
        ExampleCalculation("foo", value=1, extra=2)
