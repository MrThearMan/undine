from __future__ import annotations

import re
from typing import Callable, NamedTuple

import pytest
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from tests.helpers import parametrize_helper
from undine import Entrypoint, Field, GQLInfo, InterfaceField, InterfaceType, QueryType, RootType, create_schema
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveRepeatedError, DirectiveVersionError, FederationFeatureVersionError
from undine.federation import (
    AuthenticatedDirective,
    CacheTagDirective,
    ComposeDirectiveDirective,
    ContextDirective,
    CostDirective,
    FromContextDirective,
    InterfaceObjectDirective,
    KeyDirective,
    ListSizeDirective,
    PolicyDirective,
    RequiresScopesDirective,
    ShareableDirective,
    create_federation_schema,
)
from undine.federation.directives import (
    USED_FEDERATION_DIRECTIVES,
    ExternalDirective,
    InaccessibleDirective,
    LinkDirective,
    OverrideDirective,
    ProvidesDirective,
    RequiresDirective,
    TagDirective,
)
from undine.utils.graphql.type_registry import DIRECTIVE_REGISTRY

# Registration behavior


def test_federation_directives__not_auto_registered() -> None:
    assert "key" not in DIRECTIVE_REGISTRY
    assert "shareable" not in DIRECTIVE_REGISTRY
    assert "link" not in DIRECTIVE_REGISTRY


def test_key_directive__self_registers_on_use() -> None:
    assert KeyDirective not in USED_FEDERATION_DIRECTIVES

    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()

    assert KeyDirective in USED_FEDERATION_DIRECTIVES
    assert DIRECTIVE_REGISTRY["key"] is KeyDirective


def test_shareable_directive__self_registers_on_field_use() -> None:
    class TaskType(QueryType[Task]):
        name = Field() @ ShareableDirective()

    assert ShareableDirective in USED_FEDERATION_DIRECTIVES
    assert DIRECTIVE_REGISTRY["shareable"] is ShareableDirective


def test_federation_directives__do_not_leak_into_create_schema() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)
    directive_names = {d.name for d in schema.directives}
    assert "key" not in directive_names
    assert "shareable" not in directive_names
    assert "link" not in directive_names


def test_federation_directive__on_interface_type_included_in_link_import() -> None:
    @KeyDirective(fields="name")
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    assert '"@key"' in sdl


# KeyDirective


def test_key_directive__empty_fields_raises() -> None:
    with pytest.raises(ValueError, match="non-empty FieldSet"):
        KeyDirective(fields="")


def test_key_directive__whitespace_only_raises() -> None:
    with pytest.raises(ValueError, match="non-empty FieldSet"):
        KeyDirective(fields="   ")


def test_key_directive__added_to_query_type_directives() -> None:
    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()

    assert any(isinstance(d, KeyDirective) for d in TaskType.__directives__)


def test_key_directive__in_sdl() -> None:
    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    assert 'type TaskType @key(fields: "id")' in sdl


def test_key_directive__resolvable_false_in_sdl() -> None:
    @KeyDirective(fields="id", resolvable=False)
    class TaskType(QueryType[Task]):
        id = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    assert "resolvable: false" in sdl


def test_key_directive__repeatable() -> None:
    @KeyDirective(fields="id")
    @KeyDirective(fields="name")
    class TaskType(QueryType[Task]):
        id = Field()
        name = Field()

        @classmethod
        def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> Task | None:
            return None

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    assert sdl.count("@key(") == 2


def test_key_directive__on_interface_at_2_3_passes(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.3"

    @KeyDirective(fields="name")
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    assert 'interface Named @key(fields: "name")' in sdl


def test_key_directive__on_interface_below_2_3_raises(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.2"

    with pytest.raises(FederationFeatureVersionError):

        @KeyDirective(fields="name")
        class Named(InterfaceType):
            name = InterfaceField(GraphQLNonNull(GraphQLString))


def test_key_directive__on_query_type_at_any_version_passes(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.0"

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    assert any(isinstance(d, KeyDirective) for d in TaskType.__directives__)


# ShareableDirective


def test_shareable_directive__on_query_type_sdl() -> None:
    @ShareableDirective()
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    assert "type TaskType @shareable" in sdl


def test_shareable_directive__on_field_sdl() -> None:
    class TaskType(QueryType[Task]):
        name = Field() @ ShareableDirective()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    assert "name: String! @shareable" in sdl


def test_shareable_directive__single_application_below_2_2_passes(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.1"

    class TaskType(QueryType[Task]):
        name = Field() @ ShareableDirective()

    assert ShareableDirective in USED_FEDERATION_DIRECTIVES


def test_shareable_directive__repeated_on_field_below_2_2_raises(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.1"

    with pytest.raises(DirectiveRepeatedError):

        class TaskType(QueryType[Task]):
            name = Field() @ ShareableDirective() @ ShareableDirective()


def test_shareable_directive__repeated_on_type_below_2_2_raises(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.1"

    with pytest.raises(DirectiveRepeatedError):

        @ShareableDirective()
        @ShareableDirective()
        class TaskType(QueryType[Task]):
            name = Field()


def test_shareable_directive__repeated_on_field_at_2_2_passes(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.2"

    class TaskType(QueryType[Task]):
        name = Field() @ ShareableDirective() @ ShareableDirective()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    assert sdl.count("@shareable") >= 2


def test_shareable_directive__is_repeatable_reflects_federation_version(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.1"
    assert ShareableDirective.__is_repeatable__ is False
    assert ShareableDirective().__is_repeatable__ is False

    undine_settings.FEDERATION_VERSION = "2.2"
    assert ShareableDirective.__is_repeatable__ is True
    assert ShareableDirective().__is_repeatable__ is True


# ExternalDirective


def test_external_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field() @ ExternalDirective()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "pk: Int! @external" in sdl
    assert '"@external"' in sdl


# RequiresDirective


def test_requires_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ RequiresDirective(fields="pk")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '@requires(fields: "pk")' in sdl
    assert '"@requires"' in sdl


def test_requires_directive__empty_fields_raises() -> None:
    with pytest.raises(ValueError, match="non-empty FieldSet"):
        RequiresDirective(fields="")


# ProvidesDirective


def test_provides_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ ProvidesDirective(fields="pk")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '@provides(fields: "pk")' in sdl
    assert '"@provides"' in sdl


# OverrideDirective


def test_override_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ OverrideDirective(from_="users")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    assert '@override(from: "users")' in sdl
    assert '"@override"' in sdl
    assert "label:" not in sdl


def test_override_directive__with_label_in_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ OverrideDirective(from_="users", label="percent(25)")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    assert '@override(from: "users", label: "percent(25)")' in sdl


def test_override_directive__label_below_min_version_raises(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.6"

    with pytest.raises(DirectiveVersionError):
        OverrideDirective(from_="users", label="percent(25)")


def test_override_directive__label_at_min_version_passes(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.7"

    directive = OverrideDirective(from_="users", label="percent(25)")
    assert directive is not None


def test_override_directive__no_label_ignores_version_gate(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.0"

    directive = OverrideDirective(from_="users")
    assert directive is not None


# InaccessibleDirective


def test_inaccessible_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ InaccessibleDirective()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "name: String! @inaccessible" in sdl
    assert '"@inaccessible"' in sdl


# TagDirective


def test_inaccessible_directive__on_query_type_sdl() -> None:
    @InaccessibleDirective()
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "@inaccessible" in sdl


def test_tag_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ TagDirective(name="private")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '@tag(name: "private")' in sdl
    assert '"@tag"' in sdl


def test_tag_directive__repeatable() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ TagDirective(name="a") @ TagDirective(name="b")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert sdl.count("@tag(") == 2


# ProvidesDirective validation


def test_provides_directive__empty_fields_raises() -> None:
    with pytest.raises(ValueError, match="non-empty FieldSet"):
        ProvidesDirective(fields="")


def test_provides_directive__whitespace_only_raises() -> None:
    with pytest.raises(ValueError, match="non-empty FieldSet"):
        ProvidesDirective(fields="   ")


# LinkDirective


def test_link_directive__connected_registers_class() -> None:
    assert "link" not in DIRECTIVE_REGISTRY

    directive = LinkDirective(url="https://specs.apollo.dev/federation/v2.15")
    directive.__connected__(object())

    assert DIRECTIVE_REGISTRY["link"] is LinkDirective

    directive.__connected__(object())
    assert DIRECTIVE_REGISTRY["link"] is LinkDirective


# ComposeDirectiveDirective


def test_compose_directive_directive__in_sdl() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(
        query=Query,
        schema_definition_directives=[ComposeDirectiveDirective(name="@custom")],
    )

    sdl = schema.extensions["undine_federation_sdl"]
    assert '@composeDirective(name: "@custom")' in sdl
    assert '"@composeDirective"' in sdl


def test_compose_directive_directive__custom_directive_definition_in_service_sdl() -> None:
    # Regression: the `_service.sdl` string must include definitions of user-defined directives
    # referenced via @composeDirective. Router composition rejects the subgraph otherwise.
    class CustomDirective(Directive, locations=[DirectiveLocation.OBJECT], schema_name="custom"): ...

    @CustomDirective()
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(
        query=Query,
        schema_definition_directives=[ComposeDirectiveDirective(name="@custom")],
    )

    sdl = schema.extensions["undine_federation_sdl"]
    assert "directive @custom on OBJECT" in sdl


def test_service_sdl__excludes_federation_builtin_directive_definitions() -> None:
    # Federation built-in directives (@key, @external, ...) are imported via @link and must not
    # be redefined in `_service.sdl` or composition rejects duplicate definitions.
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "directive @key" not in sdl


def test_compose_directive_directive__below_min_version_raises(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.0"

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    with pytest.raises(DirectiveVersionError):
        create_federation_schema(
            query=Query,
            schema_definition_directives=[ComposeDirectiveDirective(name="@custom")],
        )


def test_compose_directive_directive__at_min_version_passes(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.1"

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    create_federation_schema(
        query=Query,
        schema_definition_directives=[ComposeDirectiveDirective(name="@custom")],
    )
    assert ComposeDirectiveDirective in USED_FEDERATION_DIRECTIVES


# InterfaceObjectDirective


def test_interface_object_directive__in_sdl() -> None:
    @InterfaceObjectDirective()
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "@interfaceObject" in sdl
    assert '"@interfaceObject"' in sdl


def test_interface_object_directive__below_min_version_raises(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.2"

    with pytest.raises(DirectiveVersionError):

        @InterfaceObjectDirective()
        @KeyDirective(fields="pk")
        class TaskType(QueryType[Task]):
            pk = Field()


def test_interface_object_directive__at_min_version_passes(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.3"

    @InterfaceObjectDirective()
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    assert InterfaceObjectDirective in USED_FEDERATION_DIRECTIVES


# AuthenticatedDirective


def test_authenticated_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ AuthenticatedDirective()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "@authenticated" in sdl
    assert '"@authenticated"' in sdl


# RequiresScopesDirective


def test_requires_scopes_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ RequiresScopesDirective(scopes=[["read:task"]])

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '@requiresScopes(scopes: [["read:task"]])' in sdl
    assert '"@requiresScopes"' in sdl


# PolicyDirective


def test_policy_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ PolicyDirective(policies=[["policy_a"], ["policy_b"]])

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '@policy(policies: [["policy_a"], ["policy_b"]])' in sdl
    assert '"@policy"' in sdl


# ContextDirective


def test_context_directive__on_query_type_sdl() -> None:
    @ContextDirective(name="workspace")
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '@context(name: "workspace")' in sdl
    assert '"@context"' in sdl


# FromContextDirective


def test_from_context_directive__in_link_import() -> None:
    class ScopedDirective(
        Directive,
        locations=[DirectiveLocation.FIELD_DEFINITION],
        schema_name="scoped",
    ):
        workspace = DirectiveArgument(
            GraphQLNonNull(GraphQLString),
            directives=[FromContextDirective(field="$workspace { id }")],
        )

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '"@fromContext"' in sdl
    assert FromContextDirective in USED_FEDERATION_DIRECTIVES


# CostDirective


def test_cost_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ CostDirective(weight=5)

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "@cost(weight: 5)" in sdl
    assert '"@cost"' in sdl


# ListSizeDirective


def test_list_size_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ ListSizeDirective(assumed_size=100)

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "@listSize(assumedSize: 100)" in sdl
    assert '"@listSize"' in sdl


def test_list_size_directive__slicing_arguments_in_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ ListSizeDirective(
            slicing_arguments=["first", "last"],
            sized_fields=["edges"],
        )

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert 'slicingArguments: ["first", "last"]' in sdl
    assert 'sizedFields: ["edges"]' in sdl


# CacheTagDirective


def test_cache_tag_directive__on_field_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ CacheTagDirective(format="task:{$response.pk}:name")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '@cacheTag(format: "task:{$response.pk}:name")' in sdl
    assert '"@cacheTag"' in sdl


def test_cache_tag_directive__on_query_type_sdl() -> None:
    @CacheTagDirective(format="task")
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '@cacheTag(format: "task")' in sdl


def test_cache_tag_directive__repeatable() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ CacheTagDirective(format="a") @ CacheTagDirective(format="b")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert sdl.count("@cacheTag(") == 2


def test_cache_tag_directive__below_min_version_raises(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.11"

    with pytest.raises(DirectiveVersionError):

        class TaskType(QueryType[Task]):
            pk = Field()
            name = Field() @ CacheTagDirective(format="task")


def test_cache_tag_directive__exact_min_version_passes(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.12"

    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ CacheTagDirective(format="task")

    assert CacheTagDirective in USED_FEDERATION_DIRECTIVES


# link__Import object form


def test_link_directive__import_object_form_in_sdl() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(
        query=Query,
        schema_definition_directives=[
            LinkDirective(
                url="https://example.com/custom/v1.0",
                import_=[{"name": "@key", "as": "@uniqueKey"}],
            ),
        ],
    )

    sdl = schema.extensions["undine_federation_sdl"]
    assert re.search(r'\{\s*name:\s*"@key",\s*as:\s*"@uniqueKey"\s*\}', sdl)


# Version compatibility


def test_version_validation__lower_version_raises(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.3"

    with pytest.raises(DirectiveVersionError):

        class TaskType(QueryType[Task]):
            pk = Field()
            name = Field() @ AuthenticatedDirective()


def test_version_validation__cost_below_min_raises(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.8"

    with pytest.raises(DirectiveVersionError):

        class TaskType(QueryType[Task]):
            pk = Field()
            name = Field() @ CostDirective(weight=1)


def test_version_validation__exact_min_version_passes(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.5"

    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ AuthenticatedDirective()

    assert AuthenticatedDirective in USED_FEDERATION_DIRECTIVES


def test_version_validation__higher_version_does_not_raise(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.11"

    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ AuthenticatedDirective()

    assert AuthenticatedDirective in USED_FEDERATION_DIRECTIVES


# Table-driven per-directive version gate sweep


class _GateParams(NamedTuple):
    directive_cls: type[Directive]
    apply: Callable[[], None]
    min_version: str | None


def _apply_key() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()


def _apply_shareable() -> None:
    class TaskType(QueryType[Task]):
        name = Field() @ ShareableDirective()


def _apply_external() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field() @ ExternalDirective()


def _apply_requires() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ RequiresDirective(fields="pk")


def _apply_provides() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ ProvidesDirective(fields="pk")


def _apply_override() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ OverrideDirective(from_="legacy")


def _apply_inaccessible() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ InaccessibleDirective()


def _apply_tag() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ TagDirective(name="public")


def _apply_compose_directive() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    create_federation_schema(
        query=Query,
        schema_definition_directives=[ComposeDirectiveDirective(name="@custom")],
    )


def _apply_interface_object() -> None:
    @InterfaceObjectDirective()
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()


def _apply_authenticated() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ AuthenticatedDirective()


def _apply_requires_scopes() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ RequiresScopesDirective(scopes=[["read"]])


def _apply_policy() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ PolicyDirective(policies=[["p"]])


def _apply_context() -> None:
    @ContextDirective(name="workspace")
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()


def _apply_from_context() -> None:
    class ScopedDirective(
        Directive,
        locations=[DirectiveLocation.FIELD_DEFINITION],
        schema_name="scoped",
    ):
        workspace = DirectiveArgument(
            GraphQLNonNull(GraphQLString),
            directives=[FromContextDirective(field="$workspace { id }")],
        )


def _apply_cost() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ CostDirective(weight=5)


def _apply_list_size() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ ListSizeDirective(assumed_size=100)


def _apply_cache_tag() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ CacheTagDirective(format="task")


_GATES: dict[str, _GateParams] = {
    "key (2.0)": _GateParams(KeyDirective, _apply_key, None),
    "shareable (2.0)": _GateParams(ShareableDirective, _apply_shareable, None),
    "external (2.0)": _GateParams(ExternalDirective, _apply_external, None),
    "requires (2.0)": _GateParams(RequiresDirective, _apply_requires, None),
    "provides (2.0)": _GateParams(ProvidesDirective, _apply_provides, None),
    "override (2.0)": _GateParams(OverrideDirective, _apply_override, None),
    "inaccessible (2.0)": _GateParams(InaccessibleDirective, _apply_inaccessible, None),
    "tag (2.0)": _GateParams(TagDirective, _apply_tag, None),
    "composeDirective (2.1)": _GateParams(ComposeDirectiveDirective, _apply_compose_directive, "2.1"),
    "interfaceObject (2.3)": _GateParams(InterfaceObjectDirective, _apply_interface_object, "2.3"),
    "authenticated (2.5)": _GateParams(AuthenticatedDirective, _apply_authenticated, "2.5"),
    "requiresScopes (2.5)": _GateParams(RequiresScopesDirective, _apply_requires_scopes, "2.5"),
    "policy (2.6)": _GateParams(PolicyDirective, _apply_policy, "2.6"),
    "context (2.8)": _GateParams(ContextDirective, _apply_context, "2.8"),
    "fromContext (2.8)": _GateParams(FromContextDirective, _apply_from_context, "2.8"),
    "cost (2.9)": _GateParams(CostDirective, _apply_cost, "2.9"),
    "listSize (2.9)": _GateParams(ListSizeDirective, _apply_list_size, "2.9"),
    "cacheTag (2.12)": _GateParams(CacheTagDirective, _apply_cache_tag, "2.12"),
}

_PREVIOUS_VERSION: dict[str, str] = {
    "2.1": "2.0",
    "2.3": "2.2",
    "2.5": "2.4",
    "2.6": "2.5",
    "2.8": "2.7",
    "2.9": "2.8",
    "2.12": "2.11",
}


@pytest.mark.parametrize(**parametrize_helper(_GATES))
def test_directive_version_gate__accepts_at_supported_version(
    undine_settings, directive_cls, apply, min_version
) -> None:
    undine_settings.FEDERATION_VERSION = min_version or "2.0"

    apply()

    assert directive_cls in USED_FEDERATION_DIRECTIVES


@pytest.mark.parametrize(
    **parametrize_helper({name: params for name, params in _GATES.items() if params.min_version is not None})
)
def test_directive_version_gate__rejects_below_min_version(
    undine_settings, directive_cls, apply, min_version
) -> None:
    undine_settings.FEDERATION_VERSION = _PREVIOUS_VERSION[min_version]

    with pytest.raises(DirectiveVersionError):
        apply()
