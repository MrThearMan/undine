from __future__ import annotations

from inspect import cleandoc

import pytest
from graphql import DirectiveLocation, GraphQLArgument, GraphQLField, GraphQLNonNull, GraphQLString, Undefined

from example_project.app.models import Task
from undine import Field, InterfaceType, QueryType
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError
from undine.interface import InterfaceField


def test_interface_type__definition(undine_settings) -> None:
    undine_settings.ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS = True

    class Named(InterfaceType):
        """Description."""

        name = InterfaceField(GraphQLNonNull(GraphQLString))
        """Field description."""

    assert Named.__field_map__ == {"name": Named.name}
    assert Named.__schema_name__ == "Named"
    assert Named.__interfaces__ == []
    assert Named.__directives__ == []
    assert Named.__extensions__ == {"undine_interface": Named}
    assert Named.__attribute_docstrings__ == {"name": "Field description."}


def test_interface_type__str() -> None:
    class Named(InterfaceType):
        """Interface description."""

        name = InterfaceField(GraphQLNonNull(GraphQLString), description="Field description.")

    assert str(Named) == cleandoc(
        '''
        """Interface description."""
        interface Named {
          """Field description."""
          name: String!
        }
        '''
    )


def test_interface_type__definition__schema_name() -> None:
    class Named(InterfaceType, schema_name="NamedType"):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    assert Named.__schema_name__ == "NamedType"

    assert str(Named) == cleandoc(
        """
        interface NamedType {
          name: String!
        }
        """
    )


def test_interface_type__definition__interfaces() -> None:
    class Described(InterfaceType):
        description = InterfaceField(GraphQLNonNull(GraphQLString))

    class Named(InterfaceType, interfaces=[Described]):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    assert Named.__interfaces__ == [Described]
    assert Described.__implementations__ == [Named]

    assert Named.__concrete_implementations__() == []
    assert Described.__concrete_implementations__() == []

    assert str(Named) == cleandoc(
        """
        interface Named implements Described {
          description: String!
          name: String!
        }
        """
    )


def test_interface_type__definition__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.INTERFACE], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class Named(InterfaceType, directives=directives):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    assert Named.__directives__ == directives

    assert str(Named) == cleandoc(
        """
        interface Named @value(value: "foo") {
          name: String!
        }
        """
    )


def test_interface_type__definition__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class Named(InterfaceType, directives=directives):
            name = InterfaceField(GraphQLNonNull(GraphQLString))


def test_interface_type__definition__directives__decorator() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.INTERFACE], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    @ValueDirective(value="foo")
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    assert Named.__directives__ == [ValueDirective(value="foo")]

    assert str(Named) == cleandoc(
        """
        interface Named @value(value: "foo") {
          name: String!
        }
        """
    )


def test_interface_type__definition__extensions() -> None:
    class Named(InterfaceType, extensions={"foo": "bar"}):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    assert Named.__extensions__ == {"undine_interface": Named, "foo": "bar"}


def test_interface_type__interface_field() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    assert Named.name.output_type == GraphQLNonNull(GraphQLString)
    assert Named.name.args == {}
    assert Named.name.description is None
    assert Named.name.deprecation_reason is None
    assert Named.name.schema_name == "name"
    assert Named.name.directives == []
    assert Named.name.extensions == {"undine_interface_field": Named.name}


def test_interface_type__interface_field__str() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    assert str(Named.name) == "name: String!"


def test_interface_type__interface_field__repr() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    assert repr(Named.name) == "<undine.interface.InterfaceField(ref=<GraphQLNonNull <GraphQLScalarType 'String'>>)>"


def test_interface_type__interface_field__args() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString), args={"foo": GraphQLArgument(GraphQLString)})

    assert Named.name.args == {"foo": GraphQLArgument(GraphQLString)}

    assert str(Named.name) == cleandoc(
        """
        name(
          foo: String
        ): String!
        """
    )


def test_interface_type__interface_field__description() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString), description="Description.")

    assert Named.name.description == "Description."


def test_interface_type__interface_field__description__attribute(undine_settings) -> None:
    undine_settings.ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))
        """Description."""

    assert Named.name.description == "Description."


def test_interface_type__interface_field__deprecation_reason() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString), deprecation_reason="Deprecated field.")

    assert Named.name.deprecation_reason == "Deprecated field."


def test_interface_type__interface_field__schema_name() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString), schema_name="val")

    assert Named.name.schema_name == "val"

    assert str(Named.name) == "val: String!"


def test_interface_type__interface_field__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString), directives=[ValueDirective(value="foo")])

    assert Named.name.directives == [ValueDirective(value="foo")]

    assert str(Named.name) == 'name: String! @value(value: "foo")'


def test_interface_type__interface_field__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class Named(InterfaceType):
            name = InterfaceField(GraphQLNonNull(GraphQLString), directives=directives)


def test_interface_type__interface_field__directives__matmul() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString)) @ ValueDirective(value="foo")

    assert Named.name.directives == [ValueDirective(value="foo")]

    assert str(Named.name) == 'name: String! @value(value: "foo")'


def test_interface_type__interface_field__extensions() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString), extensions={"foo": "bar"})

    assert Named.name.extensions == {"foo": "bar", "undine_interface_field": Named.name}

    graphql_field = Named.name.as_graphql_field()
    assert graphql_field.extensions == {"foo": "bar", "undine_interface_field": Named.name}


def test_interface_type__interface_field__as_graphql_field() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    field = Named.name.as_graphql_field()

    assert isinstance(field, GraphQLField)
    assert field.type == GraphQLNonNull(GraphQLString)
    assert field.args == {}
    assert field.resolve is None
    assert field.description is None
    assert field.deprecation_reason is None
    assert field.extensions == {"undine_interface_field": Named.name}


def test_interface_type__interface_field__as_graphql_field__args() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString), args={"foo": GraphQLArgument(GraphQLString)})

    field = Named.name.as_graphql_field()

    assert isinstance(field, GraphQLField)
    assert field.args == {"foo": GraphQLArgument(GraphQLString)}


def test_interface_type__interface_field__as_undine_field() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    field = Named.name.as_undine_field()

    assert isinstance(field, Field)
    assert field.ref == Named.name
    assert field.description is Undefined
    assert field.deprecation_reason is None
    assert field.field_name == "name"
    assert field.schema_name == "name"
    assert field.directives == []
    assert field.extensions == {"undine_field": field, "undine_interface_field": Named.name}


def test_interface_type__add_to_query_type() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]): ...

    assert TaskType.__interfaces__ == [Named]
    assert list(TaskType.__field_map__) == ["name"]


def test_interface_type__add_to_query_type__decorator() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    @Named
    class TaskType(QueryType[Task], auto=False): ...

    assert TaskType.__interfaces__ == [Named]
    assert list(TaskType.__field_map__) == ["name"]
