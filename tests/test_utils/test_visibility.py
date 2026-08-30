from __future__ import annotations

import logging
from typing import Any

import pytest
from django.core.cache import caches
from django.db.models import Value
from graphql import (
    DirectiveLocation,
    GraphQLArgument,
    GraphQLDirective,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
    GraphQLUnionType,
    get_introspection_query,
    parse,
)
from graphql.pyutils import did_you_mean

from example_project.app.models import Comment, Person, Project, Task
from tests.factories import UserFactory
from tests.helpers import MockRequest
from undine import (
    Calculation,
    CalculationArgument,
    Directive,
    DirectiveArgument,
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    Input,
    InterfaceField,
    InterfaceType,
    MutationType,
    Order,
    OrderSet,
    QueryType,
    RootType,
    UnionType,
    create_schema,
)
from undine.federation import ExternalDirective, FederationField, FederationType, KeyDirective, create_federation_schema
from undine.hooks import RequestCacheHook, VisibilityCacheHook
from undine.relay import Connection
from undine.typing import DjangoExpression, DjangoRequestProtocol, GQLInfo
from undine.utils.graphql.caching import RequestCacheCalculator
from undine.utils.graphql.utils import get_fragment_definitions, get_operation_definition
from undine.utils.visibility import (
    apply_visibility,
    default_visibility_extra_context,
    directive_uses_visibility,
    federation_type_uses_visibility,
    filter_set_uses_visibility,
    get_connection_inner_type,
    has_directive_visibility_override,
    has_federation_type_visibility_override,
    has_filter_set_visibility_override,
    has_interface_type_visibility_override,
    has_member_visibility,
    has_mutation_type_visibility_override,
    has_order_set_visibility_override,
    has_query_type_visibility_override,
    has_root_type_visibility_override,
    has_union_type_visibility_override,
    interface_type_uses_visibility,
    is_default_directive_is_visible,
    is_default_federation_type_is_visible,
    is_default_filter_set_is_visible,
    is_default_interface_type_is_visible,
    is_default_mutation_type_is_visible,
    is_default_order_set_is_visible,
    is_default_query_type_is_visible,
    is_default_root_type_is_visible,
    is_default_union_type_is_visible,
    is_federation_field_visible,
    is_field_visible,
    is_member_visible,
    is_type_visible,
    is_visible,
    mutation_type_uses_visibility,
    named_type_uses_visibility,
    order_set_uses_visibility,
    query_type_uses_visibility,
    root_type_uses_visibility,
    schema_uses_visibility,
)


@pytest.fixture(autouse=True)
def _clear_visibility_cache(undine_settings):
    """Handle clearing the cache between runs so that cache data is not shared between tests."""
    cache = caches[undine_settings.VISIBILITY_CACHE_ALIAS]
    cache.clear()
    try:
        yield
    finally:
        cache.clear()


def test_check_type_visibility__memoized_per_request() -> None:
    calls: list[str] = []

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            calls.append("call")
            return True

    req = MockRequest()
    assert is_type_visible(TaskType, req) is True
    assert is_type_visible(TaskType, req) is True
    assert is_type_visible(TaskType, req) is True

    assert calls == ["call"]


def test_check_type_visibility__fail_closed_on_exception(caplog: pytest.LogCaptureFixture) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            msg = "boom"
            raise RuntimeError(msg)

    req = MockRequest()
    with caplog.at_level(logging.ERROR, logger="undine"):
        assert is_type_visible(TaskType, req) is False

    messages = [record.message for record in caplog.records if record.levelno >= logging.ERROR]
    assert messages == [f"Visibility check for {TaskType!r} failed; treating as hidden."]


def test_check_member_visibility__memoized_per_request() -> None:
    calls: list[str] = []

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            calls.append("call")
            return True

    field = TaskType.__field_map__["name"]

    req = MockRequest()
    assert is_member_visible(field, req) is True
    assert is_member_visible(field, req) is True
    assert is_member_visible(field, req) is True

    assert calls == ["call"]


def test_check_member_visibility__fail_closed_on_exception(caplog: pytest.LogCaptureFixture) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            msg = "boom"
            raise RuntimeError(msg)

    field = TaskType.__field_map__["name"]
    req = MockRequest()

    with caplog.at_level(logging.ERROR, logger="undine"):
        assert is_member_visible(field, req) is False

    messages = [record.message for record in caplog.records if record.levelno >= logging.ERROR]
    assert messages == [
        f"Visibility check for {field!r} failed; treating as hidden.",
    ]


def test_check_visibility__memo_attribute_can_be_changed(undine_settings) -> None:
    undine_settings.VISIBILITY_MEMO_ATTRIBUTE = "_custom_visibility_memo"

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    request = MockRequest()
    assert is_type_visible(TaskType, request) is True

    assert request._custom_visibility_memo.results == {id(TaskType): True}
    assert not hasattr(request, "_undine_visibility_memo")


def test_check_visibility__cyclic_type_graph(caplog: pytest.LogCaptureFixture) -> None:
    """Types can refer back to themselves through their fields, e.g. 'Task.project.tasks'."""

    # The hidden fields are what force the check into the relations,
    # since a type is visible as soon as any one of its fields is.
    class ProjectType(QueryType[Project], auto=False):
        name = Field()
        tasks = Field()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return False

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return False

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    task_object_type = schema.get_type("TaskType")

    req = MockRequest()
    with caplog.at_level(logging.ERROR, logger="undine"):
        assert is_visible(task_object_type, req) is True

    assert [record.message for record in caplog.records] == []


def test_is_default_root_type_is_visible__detects_default() -> None:
    class Query(RootType):
        @Entrypoint
        def hello(self) -> str:
            return "world"

    class Hidden(RootType):
        @Entrypoint
        def hello(self) -> str:
            return "world"

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert is_default_root_type_is_visible(Query.__is_visible__) is True
    assert is_default_root_type_is_visible(Hidden.__is_visible__) is False


def test_is_default_query_type_is_visible__detects_default() -> None:
    class NoOverride(QueryType[Project], auto=False):
        pk = Field()

    class WithOverride(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert is_default_query_type_is_visible(NoOverride.__is_visible__) is True
    assert is_default_query_type_is_visible(WithOverride.__is_visible__) is False


def test_is_default_mutation_type_is_visible__detects_default() -> None:
    class NoOverrideCreate(MutationType[Task], auto=False):
        pk = Input()

    class WithOverrideCreate(MutationType[Project], auto=False):
        pk = Input()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert is_default_mutation_type_is_visible(NoOverrideCreate.__is_visible__) is True
    assert is_default_mutation_type_is_visible(WithOverrideCreate.__is_visible__) is False


def test_is_default_interface_type_is_visible__detects_default() -> None:
    class NoOverride(InterfaceType):
        name = InterfaceField(GraphQLString)

    class WithOverride(InterfaceType):
        name = InterfaceField(GraphQLString)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert is_default_interface_type_is_visible(NoOverride.__is_visible__) is True
    assert is_default_interface_type_is_visible(WithOverride.__is_visible__) is False


def test_is_default_union_type_is_visible__detects_default() -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class ProjectType(QueryType[Project], auto=False):
        pk = Field()

    class NoOverride(UnionType[TaskType, ProjectType]): ...

    class WithOverride(UnionType[TaskType, ProjectType]):
        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert is_default_union_type_is_visible(NoOverride.__is_visible__) is True
    assert is_default_union_type_is_visible(WithOverride.__is_visible__) is False


def test_is_default_filter_set_is_visible__detects_default() -> None:
    class NoOverride(FilterSet[Task], auto=False):
        name = Filter()

    class WithOverride(FilterSet[Task], auto=False):
        name = Filter()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert is_default_filter_set_is_visible(NoOverride.__is_visible__) is True
    assert is_default_filter_set_is_visible(WithOverride.__is_visible__) is False


def test_is_default_order_set_is_visible__detects_default() -> None:
    class NoOverride(OrderSet[Task], auto=False):
        name = Order()

    class WithOverride(OrderSet[Task], auto=False):
        name = Order()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert is_default_order_set_is_visible(NoOverride.__is_visible__) is True
    assert is_default_order_set_is_visible(WithOverride.__is_visible__) is False


def test_is_default_directive_is_visible__detects_default() -> None:
    class NoOverride(Directive, locations=[DirectiveLocation.OBJECT]): ...

    class WithOverride(Directive, locations=[DirectiveLocation.OBJECT]):
        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert is_default_directive_is_visible(NoOverride.__is_visible__) is True
    assert is_default_directive_is_visible(WithOverride.__is_visible__) is False


def test_is_default_federation_type_is_visible__detects_default() -> None:
    @KeyDirective(fields="id", resolvable=False)
    class NoOverride(FederationType, schema_name="NoOverrideFT"):
        id = FederationField(int)

    @KeyDirective(fields="id", resolvable=False)
    class WithOverride(FederationType, schema_name="WithOverrideFT"):
        id = FederationField(int)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert is_default_federation_type_is_visible(NoOverride.__is_visible__) is True
    assert is_default_federation_type_is_visible(WithOverride.__is_visible__) is False


def test_has_member_visibility__detects_override() -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return True

    assert has_member_visibility(TaskType.__field_map__["pk"]) is False
    assert has_member_visibility(TaskType.__field_map__["name"]) is True


def test_has_root_type_visibility_override__detects_override() -> None:
    class NoOverride(RootType):
        @Entrypoint
        def hello(self) -> str:
            return "world"

    class WithOverride(RootType):
        @Entrypoint
        def hello(self) -> str:
            return "world"

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert has_root_type_visibility_override(NoOverride) is False
    assert has_root_type_visibility_override(WithOverride) is True


def test_has_query_type_visibility_override__detects_override() -> None:
    class NoOverride(QueryType[Task], auto=False):
        pk = Field()

    class WithOverride(QueryType[Project], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert has_query_type_visibility_override(NoOverride) is False
    assert has_query_type_visibility_override(WithOverride) is True


def test_has_mutation_type_visibility_override__detects_override() -> None:
    class NoOverrideCreate(MutationType[Task], auto=False):
        pk = Input()

    class WithOverrideCreate(MutationType[Project], auto=False):
        pk = Input()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert has_mutation_type_visibility_override(NoOverrideCreate) is False
    assert has_mutation_type_visibility_override(WithOverrideCreate) is True


def test_has_interface_type_visibility_override__detects_override() -> None:
    class NoOverride(InterfaceType):
        name = InterfaceField(GraphQLString)

    class WithOverride(InterfaceType):
        name = InterfaceField(GraphQLString)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert has_interface_type_visibility_override(NoOverride) is False
    assert has_interface_type_visibility_override(WithOverride) is True


def test_has_union_type_visibility_override__detects_override() -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class ProjectType(QueryType[Project], auto=False):
        pk = Field()

    class NoOverride(UnionType[TaskType, ProjectType]): ...

    class WithOverride(UnionType[TaskType, ProjectType]):
        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert has_union_type_visibility_override(NoOverride) is False
    assert has_union_type_visibility_override(WithOverride) is True


def test_has_filter_set_visibility_override__detects_override() -> None:
    class NoOverride(FilterSet[Task], auto=False):
        name = Filter()

    class WithOverride(FilterSet[Task], auto=False):
        name = Filter()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert has_filter_set_visibility_override(NoOverride) is False
    assert has_filter_set_visibility_override(WithOverride) is True


def test_has_order_set_visibility_override__detects_override() -> None:
    class NoOverride(OrderSet[Task], auto=False):
        name = Order()

    class WithOverride(OrderSet[Task], auto=False):
        name = Order()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert has_order_set_visibility_override(NoOverride) is False
    assert has_order_set_visibility_override(WithOverride) is True


def test_has_directive_visibility_override__detects_override() -> None:
    class NoOverride(Directive, locations=[DirectiveLocation.OBJECT]): ...

    class WithOverride(Directive, locations=[DirectiveLocation.OBJECT]):
        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert has_directive_visibility_override(NoOverride) is False
    assert has_directive_visibility_override(WithOverride) is True


def test_has_federation_type_visibility_override__detects_override() -> None:
    @KeyDirective(fields="id", resolvable=False)
    class NoOverride(FederationType, schema_name="NoOverrideFT2"):
        id = FederationField(int)

    @KeyDirective(fields="id", resolvable=False)
    class WithOverride(FederationType, schema_name="WithOverrideFT2"):
        id = FederationField(int)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    assert has_federation_type_visibility_override(NoOverride) is False
    assert has_federation_type_visibility_override(WithOverride) is True


def test_root_type_uses_visibility__detected_via_override_or_member() -> None:
    class Plain(RootType):
        @Entrypoint
        def hello(self) -> str:
            return "world"

    class OverrideOnClass(RootType):
        @Entrypoint
        def hello(self) -> str:
            return "world"

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    class OverrideOnEntrypoint(RootType):
        @Entrypoint
        def hello(self) -> str:
            return "world"

        @hello.visible
        def hello_visible(self, request: DjangoRequestProtocol) -> bool:
            return True

    assert root_type_uses_visibility(Plain) is False
    assert root_type_uses_visibility(OverrideOnClass) is True
    assert root_type_uses_visibility(OverrideOnEntrypoint) is True


def test_query_type_uses_visibility__detected_via_override_or_member_or_calc_arg() -> None:
    class Plain(QueryType[Task], auto=False):
        name = Field()

    class OverrideOnClass(QueryType[Project], auto=False):
        name = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    class OverrideOnField(QueryType[Person], auto=False):
        name = Field()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return True

    class MyCalc(Calculation[int]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:  # pragma: no cover
            return Value(self.value)

        @value.visible
        def value_visible(self, request: DjangoRequestProtocol) -> bool:
            return True

    class OverrideOnCalcArg(QueryType[Comment], auto=False):
        custom = Field(MyCalc)

    assert query_type_uses_visibility(Plain) is False
    assert query_type_uses_visibility(OverrideOnClass) is True
    assert query_type_uses_visibility(OverrideOnField) is True
    assert query_type_uses_visibility(OverrideOnCalcArg) is True


def test_mutation_type_uses_visibility__detected_via_override_or_input_member() -> None:
    class PlainCreate(MutationType[Task], auto=False):
        pk = Input()

    class OverrideOnClassCreate(MutationType[Project], auto=False):
        pk = Input()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    class OverrideOnInputCreate(MutationType[Person], auto=False):
        pk = Input()

        @pk.visible
        def pk_visible(self, request: DjangoRequestProtocol) -> bool:
            return True

    assert mutation_type_uses_visibility(PlainCreate) is False
    assert mutation_type_uses_visibility(OverrideOnClassCreate) is True
    assert mutation_type_uses_visibility(OverrideOnInputCreate) is True


def test_filter_set_uses_visibility__detected_via_override_or_member() -> None:
    class Plain(FilterSet[Task], auto=False):
        name = Filter()

    class OverrideOnClass(FilterSet[Task], auto=False):
        name = Filter()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    class OverrideOnFilter(FilterSet[Task], auto=False):
        name = Filter()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return True

    assert filter_set_uses_visibility(Plain) is False
    assert filter_set_uses_visibility(OverrideOnClass) is True
    assert filter_set_uses_visibility(OverrideOnFilter) is True


def test_order_set_uses_visibility__detected_via_override_or_member() -> None:
    class Plain(OrderSet[Task], auto=False):
        name = Order()

    class OverrideOnClass(OrderSet[Task], auto=False):
        name = Order()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    class OverrideOnOrder(OrderSet[Task], auto=False):
        name = Order()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return True

    assert order_set_uses_visibility(Plain) is False
    assert order_set_uses_visibility(OverrideOnClass) is True
    assert order_set_uses_visibility(OverrideOnOrder) is True


def test_interface_type_uses_visibility__detected_via_override_or_member() -> None:
    class Plain(InterfaceType):
        name = InterfaceField(GraphQLString)

    class OverrideOnClass(InterfaceType):
        name = InterfaceField(GraphQLString)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    class OverrideOnField(InterfaceType):
        name = InterfaceField(GraphQLString)

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return True

    assert interface_type_uses_visibility(Plain) is False
    assert interface_type_uses_visibility(OverrideOnClass) is True
    assert interface_type_uses_visibility(OverrideOnField) is True


def test_federation_type_uses_visibility__detected_via_override_or_member() -> None:
    @KeyDirective(fields="id", resolvable=False)
    class Plain(FederationType, schema_name="PlainFT"):
        id = FederationField(int)

    @KeyDirective(fields="id", resolvable=False)
    class OverrideOnClass(FederationType, schema_name="OverrideOnClassFT"):
        id = FederationField(int)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    @KeyDirective(fields="id", resolvable=False)
    class OverrideOnField(FederationType, schema_name="OverrideOnFieldFT"):
        id = FederationField(int)

        @id.visible  # noqa: A003
        def id_visible(self, request: DjangoRequestProtocol) -> bool:
            return True

    assert federation_type_uses_visibility(Plain) is False
    assert federation_type_uses_visibility(OverrideOnClass) is True
    assert federation_type_uses_visibility(OverrideOnField) is True


def test_directive_uses_visibility__no_visibility_returns_false() -> None:
    class Version(Directive, locations=[DirectiveLocation.OBJECT]):
        version = DirectiveArgument(GraphQLString)

    @Version(version="1.0.0")
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    version_directive = next(d for d in schema.directives if d.name == "Version")
    assert directive_uses_visibility(version_directive) is False


def test_directive_uses_visibility__override_detected() -> None:
    class Version(Directive, locations=[DirectiveLocation.OBJECT]):
        version = DirectiveArgument(GraphQLString)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    @Version(version="1.0.0")
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    version_directive = next(d for d in schema.directives if d.name == "Version")
    assert directive_uses_visibility(version_directive) is True


def test_directive_uses_visibility__visible_argument_detected() -> None:
    class Version(Directive, locations=[DirectiveLocation.OBJECT]):
        version = DirectiveArgument(GraphQLString)

        @version.visible
        def version_visible(self, request: DjangoRequestProtocol) -> bool:
            return True

    @Version(version="1.0.0")
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    version_directive = next(d for d in schema.directives if d.name == "Version")
    assert directive_uses_visibility(version_directive) is True


def test_schema_uses_visibility__no_visibility_returns_false() -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    assert schema_uses_visibility(schema) is False


def test_schema_uses_visibility__type_with_visibility_returns_true() -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    assert schema_uses_visibility(schema) is True


def test_schema_uses_visibility__directive_with_visibility_returns_true() -> None:
    class Version(Directive, locations=[DirectiveLocation.OBJECT]):
        version = DirectiveArgument(GraphQLString)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return True

    @Version(version="1.0.0")
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    assert schema_uses_visibility(schema) is True


def test_named_type_uses_visibility__non_undine_object_returns_false() -> None:
    plain = GraphQLObjectType("Plain", fields={"x": GraphQLField(GraphQLString)})
    assert named_type_uses_visibility(plain) is False


def test_named_type_uses_visibility__non_undine_input_returns_false() -> None:
    plain = GraphQLInputObjectType("PlainInput", fields={"x": GraphQLInputField(GraphQLString)})
    assert named_type_uses_visibility(plain) is False


def test_named_type_uses_visibility__non_undine_interface_returns_false() -> None:
    plain = GraphQLInterfaceType("PlainInterface", fields={"x": GraphQLField(GraphQLString)})
    assert named_type_uses_visibility(plain) is False


def test_named_type_uses_visibility__non_undine_union_returns_false() -> None:
    member = GraphQLObjectType("Member", fields={"x": GraphQLField(GraphQLString)})
    plain = GraphQLUnionType("PlainUnion", types=[member])
    assert named_type_uses_visibility(plain) is False


def test_named_type_uses_visibility__non_undine_enum_returns_false() -> None:
    plain = GraphQLEnumType("PlainEnum", values={"A": GraphQLEnumValue("A")})
    assert named_type_uses_visibility(plain) is False


@pytest.mark.django_db
def test_apply_visibility__no_visibility__sets_flag_false_and_returns_false(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    schema.extensions.pop(undine_settings.VISIBILITY_ACTIVE_EXTENSIONS_KEY, None)

    assert apply_visibility(schema) is False
    assert schema.extensions[undine_settings.VISIBILITY_ACTIVE_EXTENSIONS_KEY] is False


@pytest.mark.django_db
def test_apply_visibility__with_visibility__sets_flag_true_and_returns_true(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    schema.extensions[undine_settings.VISIBILITY_ACTIVE_EXTENSIONS_KEY] = False

    assert apply_visibility(schema) is True
    assert schema.extensions[undine_settings.VISIBILITY_ACTIVE_EXTENSIONS_KEY] is True


def test_get_connection_inner_type__query_type() -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    connection = Connection(TaskType)
    inner = get_connection_inner_type(connection)
    assert inner is TaskType.__output_type__()


def test_get_connection_inner_type__union_type() -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class ProjectType(QueryType[Project], auto=False):
        pk = Field()

    class Combined(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Combined)
    inner = get_connection_inner_type(connection)
    assert inner is Combined.__union_type__()


def test_get_connection_inner_type__interface_type() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLString)

    connection = Connection(Named)
    inner = get_connection_inner_type(connection)
    assert inner is Named.__interface__()


def test_default_visibility_extra_context__returns_none() -> None:
    request = MockRequest()
    assert default_visibility_extra_context(request) is None


def test_is_visible__graphql_field_without_undine_extension() -> None:
    field = GraphQLField(GraphQLString)
    request = MockRequest()
    assert is_visible(field, request) is True


def test_is_visible__graphql_input_field_without_undine_extension() -> None:
    field = GraphQLInputField(GraphQLString)
    request = MockRequest()
    assert is_visible(field, request) is True


def test_is_visible__graphql_argument_without_undine_extension() -> None:
    arg = GraphQLArgument(GraphQLString)
    request = MockRequest()
    assert is_visible(arg, request) is True


def test_is_visible__graphql_enum_value_without_undine_extension() -> None:
    value = GraphQLEnumValue("A")
    request = MockRequest()
    assert is_visible(value, request) is True


def test_is_visible__graphql_directive_without_undine_extension() -> None:
    directive = GraphQLDirective("plain", locations=[DirectiveLocation.FIELD])
    request = MockRequest()
    assert is_visible(directive, request) is True


def test_is_visible__graphql_object_type_without_undine_extension() -> None:
    obj = GraphQLObjectType("Plain", fields={"x": GraphQLField(GraphQLString)})
    request = MockRequest()
    assert is_visible(obj, request) is True


def test_is_visible__graphql_input_object_type_without_undine_extension() -> None:
    obj = GraphQLInputObjectType("PlainInput", fields={"x": GraphQLInputField(GraphQLString)})
    request = MockRequest()
    assert is_visible(obj, request) is True


def test_is_visible__graphql_interface_type_without_undine_extension() -> None:
    obj = GraphQLInterfaceType("PlainInterface", fields={"x": GraphQLField(GraphQLString)})
    request = MockRequest()
    assert is_visible(obj, request) is True


def test_is_visible__graphql_union_type_without_undine_extension() -> None:
    member = GraphQLObjectType("Member2", fields={"x": GraphQLField(GraphQLString)})
    obj = GraphQLUnionType("PlainUnion2", types=[member])
    request = MockRequest()
    assert is_visible(obj, request) is True


def test_is_visible__graphql_enum_type_without_undine_extension() -> None:
    obj = GraphQLEnumType("PlainEnum2", values={"A": GraphQLEnumValue("A")})
    request = MockRequest()
    assert is_visible(obj, request) is True


def test_is_visible__unhandled_object_returns_true() -> None:
    request = MockRequest()
    schema = GraphQLSchema(query=GraphQLObjectType("Q", fields={"x": GraphQLField(GraphQLString)}))
    assert is_visible(schema, request) is True  # type: ignore[arg-type]


def test_is_field_visible__interface_field_ref__hidden_interface_returns_false() -> None:
    # When the InterfaceType itself is hidden, inherited fields are hidden too.
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    @Named
    class TaskType(QueryType[Task], auto=False): ...

    class Query(RootType):
        items = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    task_object = schema.get_type("TaskType")

    assert isinstance(task_object, GraphQLObjectType)

    name_field = task_object.fields["name"]

    request = MockRequest()
    assert is_field_visible(name_field, request) is False


def test_is_field_visible__interface_field_ref__hidden_member_returns_false() -> None:
    # `is_field_visible` is called by `any_field_visible` while scanning a QueryType's fields.
    # When the field's ref is an `InterfaceField` whose per-member visible-hook returns False,
    # the field must be hidden even if the interface type itself is visible.
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return False

    @Named
    class TaskType(QueryType[Task], auto=False): ...

    class Query(RootType):
        items = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    task_object = schema.get_type("TaskType")

    assert isinstance(task_object, GraphQLObjectType)

    name_field = task_object.fields["name"]

    request = MockRequest()
    assert is_field_visible(name_field, request) is False


def test_is_federation_field_visible__hidden_member_returns_false() -> None:
    # `is_federation_field_visible` is called by `any_federation_field_visible`.
    # When the FederationField's per-member visible-hook returns False, the field is hidden.
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="BookForFedFieldTest"):
        isbn = FederationField(str)
        title = FederationField(str) @ ExternalDirective()

        @title.visible
        def title_visible(self, request: DjangoRequestProtocol) -> bool:
            return False

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        items = Entrypoint(TaskType, many=True)

    schema = create_federation_schema(query=Query)
    book_object = schema.get_type("BookForFedFieldTest")

    assert isinstance(book_object, GraphQLObjectType)

    title_field = book_object.fields["title"]

    request = MockRequest()
    assert is_federation_field_visible(title_field, request) is False


@pytest.mark.django_db
def test_visibility_cache_hook__enabled__caches_introspection(graphql, undine_settings) -> None:
    undine_settings.VISIBILITY_CACHE_TIMEOUT = 60
    undine_settings.LIFECYCLE_HOOKS = [VisibilityCacheHook]

    calls: list[int] = []

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            calls.append(1)
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    intro = get_introspection_query(descriptions=False)

    response_1 = graphql(intro, operation_name="IntrospectionQuery")
    assert response_1.has_errors is False, response_1.errors

    first_call_count = len(calls)
    assert first_call_count == 1

    response_2 = graphql(intro, operation_name="IntrospectionQuery")
    assert response_2.has_errors is False, response_2.errors

    second_call_count = len(calls)
    assert second_call_count == 1


@pytest.mark.django_db
def test_visibility_cache_hook__disabled__no_caching(graphql, undine_settings) -> None:
    undine_settings.VISIBILITY_CACHE_TIMEOUT = 0
    undine_settings.LIFECYCLE_HOOKS = [VisibilityCacheHook]

    calls: list[int] = []

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            calls.append(1)
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    intro = get_introspection_query(descriptions=False)

    response_1 = graphql(intro, operation_name="IntrospectionQuery")
    assert response_1.has_errors is False, response_1.errors

    first_call_count = len(calls)
    assert first_call_count == 1

    response_2 = graphql(intro, operation_name="IntrospectionQuery")
    assert response_2.has_errors is False, response_2.errors

    second_call_count = len(calls)
    assert second_call_count == 2


@pytest.mark.django_db
def test_visibility_cache_hook__ignores_non_introspection_queries(graphql, undine_settings) -> None:
    undine_settings.VISIBILITY_CACHE_TIMEOUT = 60
    undine_settings.LIFECYCLE_HOOKS = [VisibilityCacheHook]

    calls: list[int] = []

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            calls.append(1)
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "{ tasks { pk } }"

    response_ = graphql(query)
    assert response_.has_errors is False, response_.errors

    assert len(calls) == 1

    response_2 = graphql(query)
    assert response_2.has_errors is False, response_2.errors

    assert len(calls) == 2


@pytest.mark.django_db
def test_visibility_cache_hook__distinguishes_users(graphql, undine_settings) -> None:
    undine_settings.VISIBILITY_CACHE_TIMEOUT = 60
    undine_settings.LIFECYCLE_HOOKS = [VisibilityCacheHook]

    calls: list[int] = []

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            calls.append(1)
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    user_1 = UserFactory.create()
    user_2 = UserFactory.create()

    query = get_introspection_query(descriptions=False)

    # Anonymous user
    response_1 = graphql(query, operation_name="IntrospectionQuery")
    assert response_1.has_errors is False, response_1.errors

    assert len(calls) == 1

    # Authenticated user 1
    graphql.force_login(user=user_1)
    response_2 = graphql(query, operation_name="IntrospectionQuery")
    assert response_2.has_errors is False, response_2.errors

    assert len(calls) == 2

    # Authenticated user 1 again
    response_3 = graphql(query, operation_name="IntrospectionQuery")
    assert response_3.has_errors is False, response_3.errors

    assert len(calls) == 2

    # Authenticated user 2
    graphql.force_login(user=user_2)

    response_4 = graphql(query, operation_name="IntrospectionQuery")
    assert response_4.has_errors is False, response_4.errors

    assert len(calls) == 3


@pytest.mark.django_db
def test_visibility_cache_hook__extra_context_influences_key(graphql, undine_settings) -> None:
    def extra(request: DjangoRequestProtocol) -> Any:
        return request.headers.get("Accept-Language")

    undine_settings.VISIBILITY_CACHE_TIMEOUT = 60
    undine_settings.LIFECYCLE_HOOKS = [VisibilityCacheHook]
    undine_settings.VISIBILITY_CACHE_EXTRA_CONTEXT = extra

    calls: list[int] = []

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            calls.append(1)
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    response_1 = graphql(query, operation_name="IntrospectionQuery", headers={"Accept-Language": "en"})
    assert response_1.has_errors is False, response_1.errors

    assert len(calls) == 1

    response_2 = graphql(query, operation_name="IntrospectionQuery", headers={"Accept-Language": "en"})
    assert response_2.has_errors is False, response_2.errors

    assert len(calls) == 1

    # Different language
    response_3 = graphql(query, operation_name="IntrospectionQuery", headers={"Accept-Language": "fi"})
    assert response_3.has_errors is False, response_3.errors

    assert len(calls) == 2


@pytest.mark.django_db
def test_did_you_mean__auto_disabled_when_schema_uses_visibility(undine_settings) -> None:
    undine_settings.ALLOW_DID_YOU_MEAN_SUGGESTIONS = True

    did_you_mean.__globals__["MAX_LENGTH"] = 5

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    create_schema(query=Query)

    assert did_you_mean.__globals__["MAX_LENGTH"] == 0


@pytest.mark.django_db
def test_request_cache_hook__auto_per_user_on_visibility_hook(graphql, undine_settings) -> None:
    undine_settings.LIFECYCLE_HOOKS = [RequestCacheHook]

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True, cache_time=60, cache_per_user=False)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "{ tasks { pk } }"

    doc = parse(query)
    operation = get_operation_definition(doc, None)
    fragments = get_fragment_definitions(doc)
    calculator = RequestCacheCalculator(operation, fragments)

    results = calculator.run()

    assert results.cache_time == 60
    assert results.cache_per_user is True
