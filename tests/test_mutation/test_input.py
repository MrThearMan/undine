from __future__ import annotations

import pytest
from graphql import DirectiveLocation, GraphQLList, GraphQLNonNull, GraphQLString, Undefined

from example_project.app.models import Project, Task
from tests.helpers import exact, mock_gql_info
from undine import Input, MutationType
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError, GraphQLPermissionError
from undine.mutation import MutationTypeMeta
from undine.typing import GQLInfo


def test_input__repr() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input()

    assert repr(MyMutationType.name) == "<undine.mutation.Input(ref=<django.db.models.fields.CharField: name>)>"


def test_input__attributes() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input()

    assert MyMutationType.name.ref == Task._meta.get_field("name")
    assert MyMutationType.name.many is False
    assert MyMutationType.name.required is False
    assert MyMutationType.name.hidden is False
    assert MyMutationType.name.default_value is Undefined
    assert MyMutationType.name.description is None
    assert MyMutationType.name.deprecation_reason is None
    assert MyMutationType.name.schema_name == "name"
    assert MyMutationType.name.directives == []
    assert MyMutationType.name.extensions == {"undine_input": MyMutationType.name}

    assert MyMutationType.name.mutation_type == MyMutationType
    assert MyMutationType.name.name == "name"


def test_input__get_field_type() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input()

    field_type = MyMutationType.name.get_field_type()
    assert field_type == GraphQLString


def test_input__as_graphql_input_field() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input()

    graphql_input_field = MyMutationType.name.as_graphql_input_field()
    assert graphql_input_field.type == GraphQLString
    assert graphql_input_field.description is None
    assert graphql_input_field.deprecation_reason is None
    assert graphql_input_field.extensions == {"undine_input": MyMutationType.name}


def test_input__many() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input(many=True)

    assert MyMutationType.name.many is True

    field_type = MyMutationType.name.get_field_type()
    assert field_type == GraphQLList(GraphQLNonNull(GraphQLString))


def test_input__required() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input(required=True)

    assert MyMutationType.name.required is True

    field_type = MyMutationType.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLString)


def test_input__required_and_many() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input(required=True, many=True)

    assert MyMutationType.name.required is True
    assert MyMutationType.name.many is True

    field_type = MyMutationType.name.get_field_type()
    assert field_type == GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))


def test_input__input_only() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input(input_only=True)

    assert MyMutationType.name.input_only is True


def test_input__description() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input(description="Description.")

    assert MyMutationType.name.description == "Description."

    graphql_input_field = MyMutationType.name.as_graphql_input_field()
    assert graphql_input_field.description == "Description."


def test_input__description__variable() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input()
        """Description."""

    assert MyMutationType.name.description == "Description."

    graphql_input_field = MyMutationType.name.as_graphql_input_field()
    assert graphql_input_field.description == "Description."


def test_input__deprecation_reason() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input(deprecation_reason="Use something else.")

    assert MyMutationType.name.deprecation_reason == "Use something else."

    graphql_input_field = MyMutationType.name.as_graphql_input_field()
    assert graphql_input_field.deprecation_reason == "Use something else."


def test_input__schema_name() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input(schema_name="val")

    assert MyMutationType.name.schema_name == "val"

    assert str(MyMutationType.name) == "val: String"


def test_input__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.INPUT_FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class MyMutationType(MutationType[Task]):
        name = Input(directives=directives)

    assert MyMutationType.name.directives == directives

    assert str(MyMutationType.name) == 'name: String @value(value: "foo")'


def test_input__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class MyMutationType(MutationType[Task]):
            name = Input(directives=directives)

    # Model not cleaned up since error occurred in MutationType class body.
    del MutationTypeMeta.__model__


def test_input__extensions() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input(extensions={"foo": "bar"})

    assert MyMutationType.name.extensions == {"foo": "bar", "undine_input": MyMutationType.name}

    graphql_input_field = MyMutationType.name.as_graphql_input_field()
    assert graphql_input_field.extensions == {"foo": "bar", "undine_input": MyMutationType.name}


def test_input__validator() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input()
        done = Input()

        @name.validate
        def validate_name(self: Input, info: GQLInfo, value: str) -> None:
            if value == "foo":
                msg = "Name must not be 'foo'"
                raise ValueError(msg)

        @done.validate()
        def validate_done(self: Input, info: GQLInfo, *, value: bool) -> None: ...

    assert MyMutationType.name.validator_func is MyMutationType.validate_name

    with pytest.raises(ValueError, match=exact("Name must not be 'foo'")):
        MyMutationType.validate_name(MyMutationType.name, mock_gql_info(), "foo")


def test_input__permissions() -> None:
    class MyMutationType(MutationType[Task]):
        name = Input()
        done = Input()

        @name.permissions
        def name_permissions(self: Input, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

        @done.permissions()
        def done_permissions(self: Input, info: GQLInfo, value: str) -> None: ...

    assert MyMutationType.name.permissions_func is MyMutationType.name_permissions

    with pytest.raises(GraphQLPermissionError):
        MyMutationType.name_permissions(MyMutationType.name, mock_gql_info(), "foo")


def test_input__default_value() -> None:
    class TaskCreateMutation(MutationType[Task]):
        progress = Input()

    assert TaskCreateMutation.progress.default_value == 0

    class TaskUpdateMutation(MutationType[Task]):
        progress = Input()

    # No default value or updates, since updates should be fully partial.
    assert TaskUpdateMutation.progress.default_value == Undefined


def test_input__default_value__not_hashable() -> None:
    class TaskCreateMutation(MutationType[Task]):
        foo = Input(list[str], default_value=["123"])

    assert TaskCreateMutation.foo.default_value == ["123"]
    assert TaskCreateMutation.foo.convertion_func is not None


def test_input__convert_func() -> None:
    class TaskCreateMutation(MutationType[Task]):
        foo = Input(str)

        @foo.convert
        def convert_foo(self, value: str) -> str:
            return value.upper()

    assert TaskCreateMutation.foo.convertion_func is not None

    assert TaskCreateMutation.__convert_input__({"foo": "abc"}) == {"foo": "ABC"}


def test_input__related_mutation_type() -> None:
    class TaskProject(MutationType[Project], kind="related"): ...

    class TaskCreateMutation(MutationType[Task]):
        project = Input(TaskProject)

    # Related mutation type can be left out and it won't affect the current relation.
    assert TaskCreateMutation.project.default_value == Undefined
    assert TaskCreateMutation.project.required is False


def test_input__callable() -> None:
    class MyMutationType(MutationType[Task]):
        @Input
        def foo(self) -> int:
            """Description."""

    assert MyMutationType.foo.many is False
    assert MyMutationType.foo.description == "Description."
    assert MyMutationType.foo.hidden is True
    assert MyMutationType.foo.input_only is True


def test_input__callable__arguments() -> None:
    class MyMutationType(MutationType[Task]):
        @Input(required=True)
        def foo(self) -> int:
            """Description."""

    assert MyMutationType.foo.many is False
    assert MyMutationType.foo.description == "Description."
    assert MyMutationType.foo.hidden is True
    assert MyMutationType.foo.input_only is True
    assert MyMutationType.foo.required is True
