from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, TypeAlias

from graphql import (
    GraphQLArgument,
    GraphQLDirective,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLUnionType,
)

from undine.settings import undine_settings
from undine.utils.graphql.undine_extensions import (
    get_undine_calculation_argument,
    get_undine_connection,
    get_undine_directive,
    get_undine_directive_argument,
    get_undine_entrypoint,
    get_undine_federation_field,
    get_undine_federation_type,
    get_undine_field,
    get_undine_filter,
    get_undine_filterset,
    get_undine_input,
    get_undine_interface_field,
    get_undine_interface_type,
    get_undine_mutation_type,
    get_undine_order,
    get_undine_orderset,
    get_undine_query_type,
    get_undine_root_type,
    get_undine_union_type,
)
from undine.utils.graphql.utils import get_underlying_type
from undine.utils.logging import logger
from undine.utils.reflection import is_same_func, is_subclass

if TYPE_CHECKING:
    from collections.abc import Callable

    from graphql import GraphQLNamedType, GraphQLSchema

    from undine import (
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
    )
    from undine.federation import FederationField, FederationType
    from undine.relay import Connection
    from undine.typing import DjangoRequestProtocol, HasGraphQLExtensions, T

    VisibilityMember: TypeAlias = (
        CalculationArgument
        | DirectiveArgument
        | Entrypoint
        | FederationField
        | Field
        | Filter
        | Input
        | InterfaceField
        | Order
    )
    VisibilityClass: TypeAlias = type[
        RootType
        | QueryType
        | MutationType
        | InterfaceType
        | UnionType
        | FilterSet
        | OrderSet
        | Directive
        | FederationType
    ]


__all__ = [
    "apply_visibility",
    "is_visible",
]


# Public interface


def is_visible(obj: HasGraphQLExtensions, request: DjangoRequestProtocol) -> bool:  # noqa: PLR0911, PLR0912, C901
    match obj:
        case GraphQLObjectType():
            return is_named_type_visible(obj, request)

        case GraphQLInputObjectType():
            return is_named_type_visible(obj, request)

        case GraphQLInterfaceType():
            return is_named_type_visible(obj, request)

        case GraphQLUnionType():
            return is_named_type_visible(obj, request)

        case GraphQLEnumType():
            return is_named_type_visible(obj, request)

        case GraphQLDirective():
            directive = get_undine_directive(obj)
            if directive is not None:
                return is_type_visible(directive, request)

        case GraphQLField():
            entrypoint = get_undine_entrypoint(obj)
            if entrypoint is not None and not is_member_visible(entrypoint, request):
                return False

            field = get_undine_field(obj)
            if field is not None:
                if not is_member_visible(field, request):
                    return False

                from undine import InterfaceField  # noqa: PLC0415

                if isinstance(field.ref, InterfaceField):
                    if not is_type_visible(field.ref.interface_type, request):
                        return False
                    if not is_member_visible(field.ref, request):
                        return False

            interface_field = get_undine_interface_field(obj)
            if interface_field is not None and not is_member_visible(interface_field, request):
                return False

            federation_field = get_undine_federation_field(obj)
            if federation_field is not None and not is_member_visible(federation_field, request):
                return False

            return is_named_type_visible(get_underlying_type(obj.type), request)

        case GraphQLInputField():
            inpt = get_undine_input(obj)
            if inpt is not None and not is_member_visible(inpt, request):
                return False

            ftr = get_undine_filter(obj)
            if ftr is not None and not is_member_visible(ftr, request):
                return False

            return is_named_type_visible(get_underlying_type(obj.type), request)

        case GraphQLArgument():
            directive_arg = get_undine_directive_argument(obj)
            if directive_arg is not None and not is_member_visible(directive_arg, request):
                return False

            calculation_arg = get_undine_calculation_argument(obj)
            if calculation_arg is not None and not is_member_visible(calculation_arg, request):
                return False

            return is_named_type_visible(get_underlying_type(obj.type), request)

        case GraphQLEnumValue():
            order = get_undine_order(obj)
            if order is not None:
                return is_member_visible(order, request)

    return True


def apply_visibility(schema: GraphQLSchema) -> bool:
    if not schema_uses_visibility(schema):
        schema.extensions[undine_settings.VISIBILITY_ACTIVE_EXTENSIONS_KEY] = False
        return False

    schema.extensions[undine_settings.VISIBILITY_ACTIVE_EXTENSIONS_KEY] = True

    from undine.utils.graphql.introspection import patch_introspection_schema  # noqa: PLC0415
    from undine.utils.graphql.utils import disable_did_you_mean_suggestions  # noqa: PLC0415

    patch_introspection_schema()
    disable_did_you_mean_suggestions()
    return True


# Caching


def with_visibility_cache(
    func: Callable[[T, DjangoRequestProtocol], bool],
) -> Callable[[T, DjangoRequestProtocol | None], bool]:

    @wraps(func)
    def wrapper(item: T, request: DjangoRequestProtocol | None) -> bool:
        # Ignore visibility checks if not in a request context
        if request is None:  # pragma: no cover
            return True

        request_cache_attr = "_undine_visibility_cache"

        cache: dict[int, bool] | None = getattr(request, request_cache_attr, None)
        if cache is None:
            cache = {}
            try:
                setattr(request, request_cache_attr, cache)
            except (AttributeError, TypeError):  # pragma: no cover
                cache = None

        cache_key = id(item)

        if cache is not None:  # pragma: no branch
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            result = func(item, request)
        except Exception:  # noqa: BLE001
            logger.exception("Visibility check for %r failed; treating as hidden.", item)
            return False

        if cache is not None:  # pragma: no branch
            cache[cache_key] = result
        return result

    return wrapper


@with_visibility_cache
def is_type_visible(cls: VisibilityClass, request: DjangoRequestProtocol) -> bool:
    return bool(cls.__is_visible__(request))


@with_visibility_cache
def is_member_visible(member: VisibilityMember, request: DjangoRequestProtocol) -> bool:
    visible_func = member.visible_func
    if visible_func is None:
        return True

    return bool(visible_func(member, request))


@with_visibility_cache
def is_named_type_visible(named_type: GraphQLNamedType, request: DjangoRequestProtocol) -> bool:  # noqa: C901,PLR0911,PLR0912
    match named_type:
        case GraphQLObjectType():
            root_type = get_undine_root_type(named_type)
            if root_type is not None:
                if not is_type_visible(root_type, request):
                    return False
                return any_entrypoint_visible(named_type, request)

            query_type = get_undine_query_type(named_type)
            if query_type is not None:
                if not is_type_visible(query_type, request):
                    return False
                return any_field_visible(named_type, request)

            connection = get_undine_connection(named_type)
            if connection is not None:
                inner = get_connection_inner_type(connection)
                return is_named_type_visible(inner, request)

            federation_type = get_undine_federation_type(named_type)
            if federation_type is not None:
                if not is_type_visible(federation_type, request):
                    return False
                return any_federation_field_visible(named_type, request)

        case GraphQLInterfaceType():
            interface_type = get_undine_interface_type(named_type)
            if interface_type is not None:
                if not is_type_visible(interface_type, request):
                    return False
                return any_interface_field_visible(named_type, request)

        case GraphQLInputObjectType():
            mutation_type = get_undine_mutation_type(named_type)
            if mutation_type is not None:
                if not is_type_visible(mutation_type, request):
                    return False
                return any_input_visible(named_type, request)

            filterset = get_undine_filterset(named_type)
            if filterset is not None:
                if not is_type_visible(filterset, request):
                    return False
                return any_filter_visible(named_type, request)

        case GraphQLUnionType():
            union_type = get_undine_union_type(named_type)
            if union_type is not None:
                if not is_type_visible(union_type, request):
                    return False
                return any_query_type_visible(named_type, request)

        case GraphQLEnumType():
            orderset = get_undine_orderset(named_type)
            if orderset is not None:
                if not is_type_visible(orderset, request):
                    return False
                return any_order_visible(named_type, request)

    return True


# Helpers


def default_visibility_extra_context(request: DjangoRequestProtocol) -> Any:
    """Default extra-context factory for the cross-request visibility cache key."""
    return None


def any_entrypoint_visible(object_type: GraphQLObjectType, request: DjangoRequestProtocol) -> bool:
    return any(is_entrypoint_visible(field, request) for field in object_type.fields.values())


def any_field_visible(object_type: GraphQLObjectType, request: DjangoRequestProtocol) -> bool:
    return any(is_field_visible(field, request) for field in object_type.fields.values())


def any_federation_field_visible(object_type: GraphQLObjectType, request: DjangoRequestProtocol) -> bool:
    return any(is_federation_field_visible(field, request) for field in object_type.fields.values())


def any_interface_field_visible(interface_type: GraphQLInterfaceType, request: DjangoRequestProtocol) -> bool:
    return any(is_interface_field_visible(field, request) for field in interface_type.fields.values())


def any_input_visible(input_type: GraphQLInputObjectType, request: DjangoRequestProtocol) -> bool:
    return any(is_input_visible(field, request) for field in input_type.fields.values())


def any_filter_visible(input_type: GraphQLInputObjectType, request: DjangoRequestProtocol) -> bool:
    # Only count real user-defined filters. The auto-generated logical-operator fields
    # carry no `Filter` extension, and on their own they cannot perform any actual filtering,
    # so they must not keep a `FilterSet` visible when every real filter is hidden.
    return any(
        is_filter_visible(field, request)
        for field in input_type.fields.values()
        if get_undine_filter(field) is not None
    )


def any_order_visible(enum: GraphQLEnumType, request: DjangoRequestProtocol) -> bool:
    return any(is_order_visible(member, request) for member in enum.values.values())


def any_query_type_visible(union_type: GraphQLUnionType, request: DjangoRequestProtocol) -> bool:
    return any(is_named_type_visible(member, request) for member in union_type.types)


def is_entrypoint_visible(field: GraphQLField, request: DjangoRequestProtocol) -> bool:
    entrypoint = get_undine_entrypoint(field)
    if entrypoint is None:  # pragma: no cover
        # `any_entrypoint_visible` iterates a RootType's fields; every entry is an Entrypoint.
        return True

    if not is_member_visible(entrypoint, request):
        return False

    return is_named_type_visible(get_underlying_type(field.type), request)


def is_field_visible(field: GraphQLField, request: DjangoRequestProtocol) -> bool:
    undine_field = get_undine_field(field)
    if undine_field is None:  # pragma: no cover
        return True

    if not is_member_visible(undine_field, request):
        return False

    from undine import InterfaceField  # noqa: PLC0415

    if isinstance(undine_field.ref, InterfaceField):
        if not is_type_visible(undine_field.ref.interface_type, request):
            return False

        if not is_member_visible(undine_field.ref, request):
            return False

    return is_named_type_visible(get_underlying_type(field.type), request)


def is_interface_field_visible(field: GraphQLField, request: DjangoRequestProtocol) -> bool:
    interface_field = get_undine_interface_field(field)
    if interface_field is None:  # pragma: no cover
        return True

    if not is_member_visible(interface_field, request):
        return False

    return is_named_type_visible(get_underlying_type(field.type), request)


def is_federation_field_visible(field: GraphQLField, request: DjangoRequestProtocol) -> bool:
    federation_field = get_undine_federation_field(field)
    if federation_field is None:  # pragma: no cover
        return True

    if not is_member_visible(federation_field, request):
        return False

    return is_named_type_visible(get_underlying_type(field.type), request)


def is_input_visible(field: GraphQLInputField, request: DjangoRequestProtocol) -> bool:
    undine_input = get_undine_input(field)
    if undine_input is None:  # pragma: no cover
        return True

    if not is_member_visible(undine_input, request):
        return False

    return is_named_type_visible(get_underlying_type(field.type), request)


def is_filter_visible(field: GraphQLInputField, request: DjangoRequestProtocol) -> bool:
    undine_filter = get_undine_filter(field)
    if undine_filter is None:  # pragma: no cover
        return True

    if not is_member_visible(undine_filter, request):
        return False

    return is_named_type_visible(get_underlying_type(field.type), request)


def is_order_visible(value: GraphQLEnumValue, request: DjangoRequestProtocol) -> bool:
    undine_order = get_undine_order(value)
    if undine_order is None:  # pragma: no cover
        return True

    return is_member_visible(undine_order, request)


def get_connection_inner_type(connection: Connection) -> GraphQLNamedType:
    if connection.query_type is not None:
        return connection.query_type.__output_type__()
    if connection.union_type is not None:
        return connection.union_type.__union_type__()
    if connection.interface_type is not None:  # pragma: no branch
        return connection.interface_type.__interface__()

    msg = "Connection must have a query type or union type."  # pragma: no cover
    raise RuntimeError(msg)  # pragma: no cover


def is_default_root_type_is_visible(func: Callable[..., Any]) -> bool:
    from undine.entrypoint import RootType  # noqa: PLC0415

    return is_same_func(func, RootType.__is_visible__)


def is_default_query_type_is_visible(func: Callable[..., Any]) -> bool:
    from undine import QueryType  # noqa: PLC0415

    return is_same_func(func, QueryType.__is_visible__)


def is_default_mutation_type_is_visible(func: Callable[..., Any]) -> bool:
    from undine import MutationType  # noqa: PLC0415

    return is_same_func(func, MutationType.__is_visible__)


def is_default_interface_type_is_visible(func: Callable[..., Any]) -> bool:
    from undine import InterfaceType  # noqa: PLC0415

    return is_same_func(func, InterfaceType.__is_visible__)


def is_default_union_type_is_visible(func: Callable[..., Any]) -> bool:
    from undine import UnionType  # noqa: PLC0415

    return is_same_func(func, UnionType.__is_visible__)


def is_default_filter_set_is_visible(func: Callable[..., Any]) -> bool:
    from undine import FilterSet  # noqa: PLC0415

    return is_same_func(func, FilterSet.__is_visible__)


def is_default_order_set_is_visible(func: Callable[..., Any]) -> bool:
    from undine import OrderSet  # noqa: PLC0415

    return is_same_func(func, OrderSet.__is_visible__)


def is_default_directive_is_visible(func: Callable[..., Any]) -> bool:
    from undine.directives import Directive  # noqa: PLC0415

    return is_same_func(func, Directive.__is_visible__)


def is_default_federation_type_is_visible(func: Callable[..., Any]) -> bool:
    from undine.federation import FederationType  # noqa: PLC0415

    return is_same_func(func, FederationType.__is_visible__)


def has_root_type_visibility_override(cls: type[RootType]) -> bool:
    return not is_default_root_type_is_visible(cls.__is_visible__)


def has_query_type_visibility_override(cls: type[QueryType]) -> bool:
    return not is_default_query_type_is_visible(cls.__is_visible__)


def has_mutation_type_visibility_override(cls: type[MutationType]) -> bool:
    return not is_default_mutation_type_is_visible(cls.__is_visible__)


def has_interface_type_visibility_override(cls: type[InterfaceType]) -> bool:
    return not is_default_interface_type_is_visible(cls.__is_visible__)


def has_union_type_visibility_override(cls: type[UnionType]) -> bool:
    return not is_default_union_type_is_visible(cls.__is_visible__)


def has_filter_set_visibility_override(cls: type[FilterSet]) -> bool:
    return not is_default_filter_set_is_visible(cls.__is_visible__)


def has_order_set_visibility_override(cls: type[OrderSet]) -> bool:
    return not is_default_order_set_is_visible(cls.__is_visible__)


def has_directive_visibility_override(cls: type[Directive]) -> bool:
    return not is_default_directive_is_visible(cls.__is_visible__)


def has_federation_type_visibility_override(cls: type[FederationType]) -> bool:
    return not is_default_federation_type_is_visible(cls.__is_visible__)


def has_member_visibility(member: VisibilityMember) -> bool:
    return member.visible_func is not None


def schema_uses_visibility(schema: GraphQLSchema) -> bool:
    return any(named_type_uses_visibility(named_type) for named_type in schema.type_map.values()) or any(
        directive_uses_visibility(directive) for directive in schema.directives
    )


def directive_uses_visibility(directive: GraphQLDirective) -> bool:
    undine_directive = get_undine_directive(directive)
    if undine_directive is not None and has_directive_visibility_override(undine_directive):
        return True

    for arg in directive.args.values():
        directive_arg = get_undine_directive_argument(arg)
        if directive_arg is not None and has_member_visibility(directive_arg):
            return True
    return False


def named_type_uses_visibility(named_type: GraphQLNamedType) -> bool:  # noqa: C901,PLR0911,PLR0912
    match named_type:
        case GraphQLObjectType():
            query_type = get_undine_query_type(named_type)
            if query_type is not None and query_type_uses_visibility(query_type):
                return True

            federation_type = get_undine_federation_type(named_type)
            if federation_type is not None and federation_type_uses_visibility(federation_type):
                return True

            root_type = get_undine_root_type(named_type)
            if root_type is not None and root_type_uses_visibility(root_type):
                return True

        case GraphQLInputObjectType():
            mutation_type = get_undine_mutation_type(named_type)
            if mutation_type is not None and mutation_type_uses_visibility(mutation_type):
                return True

            filterset = get_undine_filterset(named_type)
            if filterset is not None and filter_set_uses_visibility(filterset):
                return True

        case GraphQLInterfaceType():
            interface_type = get_undine_interface_type(named_type)
            if interface_type is not None and interface_type_uses_visibility(interface_type):
                return True

        case GraphQLUnionType():
            union_type = get_undine_union_type(named_type)
            if union_type is not None and has_union_type_visibility_override(union_type):
                return True

        case GraphQLEnumType():
            orderset = get_undine_orderset(named_type)
            if orderset is not None and order_set_uses_visibility(orderset):
                return True

    return False


def root_type_uses_visibility(root_type: type[RootType]) -> bool:
    if has_root_type_visibility_override(root_type):
        return True
    return any(has_member_visibility(entrypoint) for entrypoint in root_type.__entrypoint_map__.values())


def query_type_uses_visibility(query_type: type[QueryType]) -> bool:
    from undine import Calculation  # noqa: PLC0415

    if has_query_type_visibility_override(query_type):
        return True

    for field in query_type.__field_map__.values():
        if has_member_visibility(field):
            return True

        if is_subclass(field.ref, Calculation):
            return any(has_member_visibility(arg) for arg in field.ref.__arguments__.values())

    return False


def mutation_type_uses_visibility(mutation_type: type[MutationType]) -> bool:
    return has_mutation_type_visibility_override(mutation_type) or any(
        has_member_visibility(input_field) for input_field in mutation_type.__input_map__.values()
    )


def filter_set_uses_visibility(filterset: type[FilterSet]) -> bool:
    return has_filter_set_visibility_override(filterset) or any(
        has_member_visibility(undine_filter) for undine_filter in filterset.__filter_map__.values()
    )


def order_set_uses_visibility(orderset: type[OrderSet]) -> bool:
    return has_order_set_visibility_override(orderset) or any(
        has_member_visibility(undine_order) for undine_order in orderset.__order_map__.values()
    )


def interface_type_uses_visibility(interface_type: type[InterfaceType]) -> bool:
    return has_interface_type_visibility_override(interface_type) or any(
        has_member_visibility(interface_field) for interface_field in interface_type.__field_map__.values()
    )


def federation_type_uses_visibility(federation_type: type[FederationType]) -> bool:
    return has_federation_type_visibility_override(federation_type) or any(
        has_member_visibility(field) for field in federation_type.__field_map__.values()
    )
