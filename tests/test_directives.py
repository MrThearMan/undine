from __future__ import annotations

from inspect import cleandoc

import pytest
from graphql import DirectiveLocation, GraphQLArgument, GraphQLDirective, GraphQLInt, GraphQLNonNull, Undefined

from example_project.app.models import Project, Task
from tests.helpers import exact
from undine import Entrypoint, Field, InterfaceField, InterfaceType, QueryType, RootType, UnionType
from undine.directives import (
    AtomicDirective,
    CacheRulesDirective,
    ComplexityDirective,
    Directive,
    DirectiveArgument,
    DirectiveList,
    SemanticNonNullDirective,
)
from undine.exceptions import (
    DirectiveLocationError,
    DirectiveRepeatedError,
    MissingDirectiveArgumentError,
    MissingDirectiveLocationsError,
    NotCompatibleWithError,
    UnexpectedDirectiveArgumentError,
)
from undine.utils.graphql.type_registry import DIRECTIVE_REGISTRY, GRAPHQL_REGISTRY
from undine.utils.reflection import is_subclass


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

    assert "value" in DIRECTIVE_REGISTRY
    assert is_subclass(DIRECTIVE_REGISTRY["value"], Directive)

    ValueDirective.__directive__()

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


def test_directive__str__instance() -> None:
    class NewDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="new"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    directive = NewDirective(value=42)

    assert str(directive) == "@new(value: 42)"


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


def test_directive__locations_missing_raises() -> None:
    with pytest.raises(MissingDirectiveLocationsError):

        class BadDirective(Directive): ...


def test_directive__init__missing_required_argument() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        required = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    with pytest.raises(MissingDirectiveArgumentError):
        ValueDirective()


def test_directive__init__unexpected_argument() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    with pytest.raises(UnexpectedDirectiveArgumentError):
        ValueDirective(value=1, extra_kwarg="oops")


def test_directive__repr__instance() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value_repr"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    directive = ValueDirective(value=7)

    assert repr(directive) == "<tests.test_directives.test_directive__repr__instance.<locals>.ValueDirective(value=7)>"


def test_directive__eq() -> None:
    class NewDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert NewDirective(value=1) == NewDirective(value=1)


def test_directive__eq__different_arg_values() -> None:
    class NewDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert NewDirective(value=1) != NewDirective(value=2)


def test_directive__eq__not_same_type() -> None:
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    class BDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert ADirective(value=1) != BDirective(value=1)


def test_directive__hash() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    d1 = ValueDirective(value=1)
    d2 = ValueDirective(value=1)

    assert hash(d1) == hash(d2)


def test_directive__hash__different_arg_values() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    d1 = ValueDirective(value=1)
    d2 = ValueDirective(value=2)

    assert hash(d1) != hash(d2)


def test_directive__connect__incompatible_type_raises() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt), default_value=0)

    directive = ValueDirective()

    class IncompatibleTarget: ...

    with pytest.raises(NotCompatibleWithError):
        directive.__connect__(IncompatibleTarget())


def test_directive__contains() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert "value" in ValueDirective

    assert "other" not in ValueDirective


# DirectiveArgument


def test_directive__argument__repr() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert repr(ValueDirective.value) == (
        "<undine.directives.DirectiveArgument(ref=<GraphQLNonNull <GraphQLScalarType 'Int'>>)>"
    )


def test_directive__argument__str() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert str(ValueDirective.value) == "value: Int!"


def test_directive__argument__attributes() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    assert ValueDirective.value.get_argument_type() == GraphQLNonNull(GraphQLInt)
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


def test_directive__argument__directives__matmul() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ARGUMENT_DEFINITION], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="my"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt)) @ ValueDirective(value=1)

    assert MyDirective.value.directives == [ValueDirective(value=1)]

    assert str(MyDirective.value) == "value: Int! @value(value: 1)"


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


def test_directive_argument__set__on_instance() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    directive = ValueDirective(value=1)
    directive.value = 99

    assert directive.value == 99


def test_directive_argument__set__on_class_raises() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

    msg = "Can't set attribute 'value' on 'ValueDirective'"
    with pytest.raises(AttributeError, match=exact(msg)):
        ValueDirective.value.__set__(None, 99)


def test_directive_argument__visible__no_func() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLInt))

        @value.visible()
        def value_visible(self, request) -> bool:
            return False

    assert ValueDirective.value.visible_func is not None


# DirectiveList


def test_directive_list__init():
    class VersionDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]):
        value = DirectiveArgument(int)

    directive = VersionDirective(value=1)

    directive_list = DirectiveList([directive], location=DirectiveLocation.FIELD_DEFINITION)

    assert directive_list.data == [directive]
    assert directive_list.location == DirectiveLocation.FIELD_DEFINITION


def test_directive_list__setitem():
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...

    class BDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    class CDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...

    directive_a = ADirective()
    directive_b = BDirective()
    directive_c = CDirective()

    directive_list = DirectiveList([directive_a, directive_b], location=DirectiveLocation.FIELD_DEFINITION)

    with pytest.raises(DirectiveRepeatedError):
        directive_list[1] = directive_a

    assert directive_list.data == [directive_a, directive_b]

    directive_list[0] = directive_b
    assert directive_list.data == [directive_b, directive_b]

    with pytest.raises(DirectiveLocationError):
        directive_list[0] = directive_c


def test_directive_list__add():
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...

    class BDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    class CDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...

    directive_a = ADirective()
    directive_b = BDirective()
    directive_c = CDirective()

    directive_list = DirectiveList([directive_a, directive_b], location=DirectiveLocation.FIELD_DEFINITION)

    with pytest.raises(DirectiveRepeatedError):
        directive_list = directive_list + [directive_a]  # noqa: PLR6104,RUF005

    assert directive_list.data == [directive_a, directive_b]

    directive_list = directive_list + [directive_b]  # noqa: PLR6104,RUF005
    assert directive_list.data == [directive_a, directive_b, directive_b]

    with pytest.raises(DirectiveLocationError):
        directive_list = directive_list + [directive_c]  # noqa: PLR6104,RUF005


def test_directive_list__iadd():
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...

    class BDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    class CDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...

    directive_a = ADirective()
    directive_b = BDirective()
    directive_c = CDirective()

    directive_list = DirectiveList([directive_a, directive_b], location=DirectiveLocation.FIELD_DEFINITION)

    with pytest.raises(DirectiveRepeatedError):
        directive_list += [directive_a]

    assert directive_list.data == [directive_a, directive_b]

    directive_list += [directive_b]
    assert directive_list.data == [directive_a, directive_b, directive_b]

    with pytest.raises(DirectiveLocationError):
        directive_list += [directive_c]


def test_directive_list__mul():
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...

    class BDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    class CDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...

    directive_a = ADirective()
    directive_b = BDirective()
    directive_c = CDirective()

    directive_list = DirectiveList([directive_a], location=DirectiveLocation.FIELD_DEFINITION)

    with pytest.raises(DirectiveRepeatedError):
        directive_list = directive_list * 2  # noqa: PLR6104,RUF100

    assert directive_list.data == [directive_a]

    directive_list.data = [directive_b]
    directive_list = directive_list * 2  # noqa: PLR6104,RUF100
    assert directive_list.data == [directive_b, directive_b]

    directive_list.data = [directive_c]
    with pytest.raises(DirectiveLocationError):
        directive_list = directive_list * 2  # noqa: PLR6104,RUF100


def test_directive_list__imul():
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...

    class BDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    class CDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...

    directive_a = ADirective()
    directive_b = BDirective()
    directive_c = CDirective()

    directive_list = DirectiveList([directive_a], location=DirectiveLocation.FIELD_DEFINITION)

    with pytest.raises(DirectiveRepeatedError):
        directive_list *= 2

    assert directive_list.data == [directive_a]

    directive_list.data = [directive_b]
    directive_list *= 2
    assert directive_list.data == [directive_b, directive_b]

    directive_list.data = [directive_c]
    with pytest.raises(DirectiveLocationError):
        directive_list *= 2


def test_directive_list__append():
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...

    class BDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    class CDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...

    directive_1 = ADirective()
    directive_2 = BDirective()
    directive_3 = CDirective()

    directive_list = DirectiveList([directive_1, directive_2], location=DirectiveLocation.FIELD_DEFINITION)

    with pytest.raises(DirectiveRepeatedError):
        directive_list.append(directive_1)

    assert directive_list.data == [directive_1, directive_2]

    directive_list.append(directive_2)
    assert directive_list.data == [directive_1, directive_2, directive_2]

    with pytest.raises(DirectiveLocationError):
        directive_list.append(directive_3)


def test_directive_list__insert():
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...

    class BDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    class CDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...

    directive_1 = ADirective()
    directive_2 = BDirective()
    directive_3 = CDirective()

    directive_list = DirectiveList([directive_1, directive_2], location=DirectiveLocation.FIELD_DEFINITION)

    with pytest.raises(DirectiveRepeatedError):
        directive_list.insert(1, directive_1)

    assert directive_list.data == [directive_1, directive_2]

    directive_list.insert(1, directive_2)
    assert directive_list.data == [directive_1, directive_2, directive_2]

    with pytest.raises(DirectiveLocationError):
        directive_list.insert(1, directive_3)


def test_directive_list__extend():
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...

    class BDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    class CDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...

    directive_a = ADirective()
    directive_b = BDirective()
    directive_c = CDirective()

    directive_list = DirectiveList([directive_a, directive_b], location=DirectiveLocation.FIELD_DEFINITION)

    with pytest.raises(DirectiveRepeatedError):
        directive_list.extend([directive_a])

    assert directive_list.data == [directive_a, directive_b]

    directive_list.extend([directive_b])
    assert directive_list.data == [directive_a, directive_b, directive_b]

    with pytest.raises(DirectiveLocationError):
        directive_list.extend([directive_c])


def test_directive_list__get_other_data__list() -> None:
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    directive_a = ADirective()

    directive_list = DirectiveList([directive_a], location=DirectiveLocation.FIELD_DEFINITION)
    result = directive_list + [directive_a]  # noqa: RUF005

    assert result.data == [directive_a, directive_a]


def test_directive_list__get_other_data__user_list() -> None:
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    directive_a = ADirective()

    list_a = DirectiveList([directive_a], location=DirectiveLocation.FIELD_DEFINITION)
    list_b = DirectiveList([directive_a], location=DirectiveLocation.FIELD_DEFINITION)

    result = list_a + list_b

    assert result.data == [directive_a, directive_a]


def test_directive_list__get_other_data__generator() -> None:
    class ADirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], is_repeatable=True): ...

    directive_a = ADirective()

    directive_list = DirectiveList([directive_a], location=DirectiveLocation.FIELD_DEFINITION)

    result = directive_list + (d for d in [directive_a])

    assert result.data == [directive_a, directive_a]


# Custom directives


def test_atomic_directive__str() -> None:
    assert str(AtomicDirective) == cleandoc(
        '''
        """
        Used to indicate that all mutations in the operation should be executed atomically.
        """
        directive @atomic on MUTATION
        '''
    )


def test_complexity_directive__str() -> None:
    assert str(ComplexityDirective) == cleandoc(
        '''
        """
        Used to indicate the complexity of resolving a field, counted towards
        the maximum query complexity of resolving a root type field.
        """
        directive @complexity(
          """The complexity of resolving the field."""
          value: Int!
        ) on FIELD_DEFINITION
        '''
    )


def test_complexity_directive__add_to_entrypoint() -> None:
    directive = ComplexityDirective(value=1)

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True) @ directive

    assert Query.tasks.complexity == 1
    assert Query.tasks.directives == [directive]


def test_complexity_directive__add_to_field() -> None:
    directive = ComplexityDirective(value=1)

    class TaskType(QueryType[Task], auto=False):
        name = Field() @ directive

    assert TaskType.name.complexity == 1
    assert TaskType.name.directives == [directive]


def test_complexity_directive__add_to_interface_field() -> None:
    directive = ComplexityDirective(value=1)

    class Named(InterfaceType, auto=False):
        name = InterfaceField(str) @ directive

    assert Named.name.complexity == 1
    assert Named.name.directives == [directive]


def test_complexity_directive__negative_value_raises() -> None:
    msg = "`value` must be a positive integer."
    with pytest.raises(ValueError, match=exact(msg)):
        ComplexityDirective(value=-1)


def test_complexity_directive__connected_no_complexity_attr() -> None:
    directive = ComplexityDirective(value=5)

    class Dummy: ...

    # Does not raise an error
    directive.__connected__(Dummy())


def test_cache_rules_directive__str() -> None:
    assert str(CacheRulesDirective) == cleandoc(
        '''
        """
        Used to define caching behavior either for a single field, or for all fields that return a particular type.
        """
        directive @cacheRules(
          """Whether the value is cached per user or not."""
          cachePerUser: Boolean! = false
          """How many seconds this field of fields of this type can be cached for."""
          cacheTime: Int!
        ) on FIELD_DEFINITION | OBJECT | INTERFACE | UNION
        '''
    )


def test_cache_rules_directive__add_to_entrypoint() -> None:
    directive = CacheRulesDirective(cache_time=1)

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True) @ directive

    assert Query.tasks.cache_time == 1
    assert Query.tasks.cache_per_user is False
    assert Query.tasks.directives == [directive]


def test_cache_rules_directive__add_to_field() -> None:
    directive = CacheRulesDirective(cache_time=1)

    class TaskType(QueryType[Task], auto=False):
        name = Field() @ directive

    assert TaskType.name.cache_time == 1
    assert TaskType.name.cache_per_user is False
    assert TaskType.name.directives == [directive]


def test_cache_rules_directive__add_to_interface_field() -> None:
    directive = CacheRulesDirective(cache_time=1)

    class Named(InterfaceType, auto=False):
        name = InterfaceField(str) @ directive

    assert Named.name.cache_time == 1
    assert Named.name.cache_per_user is False
    assert Named.name.directives == [directive]


def test_cache_rules_directive__add_to_query_type() -> None:
    directive = CacheRulesDirective(cache_time=1)

    @directive
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    assert TaskType.__cache_time__ == 1
    assert TaskType.__cache_per_user__ is False
    assert TaskType.__directives__ == [directive]


def test_cache_rules_directive__add_to_interface_type() -> None:
    directive = CacheRulesDirective(cache_time=1)

    @directive
    class Named(InterfaceType, auto=False):
        name = InterfaceField(str)

    assert Named.__cache_time__ == 1
    assert Named.__cache_per_user__ is False
    assert Named.__directives__ == [directive]


def test_cache_rules_directive__add_to_union_type() -> None:
    directive = CacheRulesDirective(cache_time=1)

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    @directive
    class Commentable(UnionType[TaskType, ProjectType]): ...

    assert Commentable.__cache_time__ == 1
    assert Commentable.__cache_per_user__ is False
    assert Commentable.__directives__ == [directive]


def test_cache_rules_directive__connected__undefined_cache_time__entrypoint(undine_settings) -> None:
    undine_settings.ENTRYPOINT_DEFAULT_CACHE_TIME = 60

    directive = CacheRulesDirective()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True) @ directive

    assert Query.tasks.cache_time == 60


def test_cache_rules_directive__connected__undefined_cache_time__entrypoint__setting_none(undine_settings) -> None:
    undine_settings.ENTRYPOINT_DEFAULT_CACHE_TIME = None

    directive = CacheRulesDirective()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    msg = "No `cache_time` defined for 'CacheRulesDirective'"
    with pytest.raises(ValueError, match=exact(msg)):

        class Query(RootType):
            tasks = Entrypoint(TaskType, many=True) @ directive


def test_cache_rules_directive__connected__undefined_cache_time__non_entrypoint() -> None:
    directive = CacheRulesDirective()

    msg = "No `cache_time` defined for 'CacheRulesDirective'"
    with pytest.raises(ValueError, match=exact(msg)):

        class TaskType(QueryType[Task], auto=False):
            name = Field() @ directive


def test_cache_rules_directive__negative_cache_time_raises() -> None:
    msg = "`cache_time` must be a positive integer."
    with pytest.raises(ValueError, match=exact(msg)):
        CacheRulesDirective(cache_time=-1)


def test_cache_rules_directive__connected__no_cache_attr() -> None:
    directive = CacheRulesDirective(cache_time=10)

    class Dummy: ...

    # Does not raise an error
    directive.__connected__(Dummy())


def test_semantic_non_null_directive__str() -> None:
    assert str(SemanticNonNullDirective) == cleandoc(
        '''
        """
        Indicates that a field is only null if there's a matching error in the `errors` array.
        """
        directive @semanticNonNull(
          """
          Which parts of a list should be considered for the non-null check.
          For an n-dimensional list, integers 0 through n-1 account for the lists and n accounts for the items.
          E.g. a regular single dimensional list: 0 for the list, 1 for the items.
          """
          levels: [Int!]! = [0]
        ) on FIELD_DEFINITION
        '''
    )


def test_semantic_non_null_directive__negative_level_raises() -> None:
    msg = "Values in `levels` must all be positive integers or zero. Found -1."
    with pytest.raises(ValueError, match=exact(msg)):
        SemanticNonNullDirective(levels=[-1])


def test_semantic_non_null_directive__default_levels() -> None:
    directive = SemanticNonNullDirective()

    assert directive.levels == [0]


def test_semantic_non_null_directive__add_to_field() -> None:
    directive = SemanticNonNullDirective(levels=[0, 1])

    class TaskType(QueryType[Task], auto=False):
        name = Field() @ directive

    assert TaskType.name.nullable is True
    assert TaskType.name.directives == [directive]


def test_semantic_non_null_directive__connected__no_nullable_attr() -> None:
    directive = SemanticNonNullDirective()

    class Dummy: ...

    # Does not raise an error
    directive.__connected__(Dummy())
