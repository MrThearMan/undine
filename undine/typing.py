from __future__ import annotations

import enum
import operator as op
from collections import defaultdict
from collections.abc import Callable
from enum import Enum, StrEnum, auto
from functools import cache
from types import FunctionType, GenericAlias, UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    NewType,
    NotRequired,
    ParamSpec,
    Protocol,
    Self,
    TypeAlias,
    TypedDict,
    TypeVar,
    TypeVarTuple,
    Union,
    runtime_checkable,
)

# Sort separately due to being a private import
from typing import _GenericAlias  # type: ignore[attr-defined]  # isort: skip  # noqa: PLC2701
from typing import _LiteralGenericAlias  # type: ignore[attr-defined]  # isort: skip  # noqa: PLC2701
from typing import _TypedDictMeta  # type: ignore[attr-defined]  # isort: skip  # noqa: PLC2701
from typing import _ProtocolMeta  # type: ignore[attr-defined]  # isort: skip  # noqa: PLC2701
from typing import _eval_type  # type: ignore[attr-defined]  # isort: skip  # noqa: PLC2701

from collections.abc import Iterable

from django.db.models import (
    Expression,
    F,
    Field,
    ForeignKey,
    ForeignObjectRel,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    Model,
    OneToOneField,
    OneToOneRel,
    Q,
    QuerySet,
    Subquery,
)
from django.db.models.query_utils import RegisterLookupMixin
from graphql import (
    FieldNode,
    FragmentSpreadNode,
    GraphQLDirective,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLNullableType,
    GraphQLObjectType,
    GraphQLResolveInfo,
    GraphQLScalarType,
    GraphQLUnionType,
    SelectionNode,
    UndefinedType,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping
    from http.cookies import SimpleCookie

    from django.contrib.auth.models import AbstractUser, AnonymousUser
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation
    from django.contrib.sessions.backends.base import SessionBase
    from django.core.files.uploadedfile import UploadedFile
    from django.db.models.sql import Query
    from django.http import QueryDict
    from django.http.request import HttpHeaders, MediaType
    from django.http.response import ResponseHeaders
    from django.test.client import Client
    from django.utils.datastructures import MultiValueDict
    from graphql import (
        DirectiveLocation,
        FragmentDefinitionNode,
        GraphQLArgumentMap,
        GraphQLFormattedError,
        GraphQLOutputType,
        GraphQLSchema,
        OperationDefinitionNode,
    )
    from graphql.pyutils import Path

    from undine import FilterSet, InterfaceType, OrderSet
    from undine.directives import Directive
    from undine.optimizer.optimizer import OptimizationData

__all__ = [
    "Annotatable",
    "CombinableExpression",
    "CompleteMessage",
    "ConnectionAckMessage",
    "ConnectionDict",
    "ConnectionInitMessage",
    "DispatchProtocol",
    "DjangoExpression",
    "DjangoHttpResponseProtocol",
    "DjangoRequestProtocol",
    "DjangoTestClientHttpResponseProtocol",
    "DocstringParserProtocol",
    "ErrorMessage",
    "GQLInfo",
    "GraphQLFilterResolver",
    "HttpMethod",
    "InputPermFunc",
    "JsonObject",
    "Lambda",
    "LiteralArg",
    "ManyMatch",
    "Message",
    "ModelField",
    "ModelManager",
    "MutationKind",
    "NextMessage",
    "NextMessagePayload",
    "NodeDict",
    "ObjectSelections",
    "OptimizerFunc",
    "PageInfoDict",
    "ParametrizedType",
    "PermissionFunc",
    "PingMessage",
    "PongMessage",
    "ProtocolType",
    "RelatedField",
    "RelatedManager",
    "Selections",
    "Self",
    "SubscribeMessage",
    "SubscribeMessagePayload",
    "SupportsLookup",
    "ToManyField",
    "ToOneField",
    "UndineErrorCodes",
    "ValidatorFunc",
]

# Misc.

TypedDictType: TypeAlias = _TypedDictMeta
ParametrizedType: TypeAlias = _GenericAlias
LiteralType: TypeAlias = _LiteralGenericAlias
ProtocolType: TypeAlias = _ProtocolMeta
PrefetchHackCacheType: TypeAlias = defaultdict[str, defaultdict[str, set[str]]]
LiteralArg: TypeAlias = str | int | bytes | bool | Enum | None
TypeHint: TypeAlias = type | UnionType | GenericAlias
JsonObject: TypeAlias = dict[str, Any] | list[dict[str, Any]]
DefaultValueType: TypeAlias = int | float | str | bool | dict | list | UndefinedType | None

# TypeVars

T = TypeVar("T")
P = ParamSpec("P")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)
TModel = TypeVar("TModel", bound=Model)
TUser = TypeVar("TUser", bound="AbstractUser", covariant=True)  # noqa: PLC0105
TTypedDict = TypeVar("TTypedDict", bound=TypedDictType)
GNT = TypeVar("GNT", bound=GraphQLNullableType)
TTypeHint = TypeVar("TTypeHint", bound=TypeHint)
TQueryTypes = TypeVarTuple("TQueryTypes")


# Literals

HttpMethod: TypeAlias = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "HEAD"]

# NewTypes

Lambda = NewType("Lambda", FunctionType)
"""
Type used to register a different implementations for lambda functions
as opposed to a regular function in the FunctionDispatcher.
"""


# Protocols


@runtime_checkable
class DocstringParserProtocol(Protocol):
    @classmethod
    def parse_body(cls, docstring: str) -> str: ...

    @classmethod
    def parse_arg_descriptions(cls, docstring: str) -> dict[str, str]: ...

    @classmethod
    def parse_return_description(cls, docstring: str) -> str: ...

    @classmethod
    def parse_raise_descriptions(cls, docstring: str) -> dict[str, str]: ...

    @classmethod
    def parse_deprecations(cls, docstring: str) -> dict[str, str]: ...


class DjangoExpression(Protocol):
    """Protocol for any expression that can be used in a Django ORM query."""

    def resolve_expression(
        self,
        query: Query,
        allow_joins: bool,  # noqa: FBT001
        reuse: set[str] | None,
        summarize: bool,  # noqa: FBT001
        for_save: bool,  # noqa: FBT001
    ) -> DjangoExpression: ...


class DispatchProtocol(Protocol[T_co]):
    def __call__(self, key: Any, **kwargs: Any) -> T_co: ...


class DjangoRequestProtocol(Protocol[TUser]):
    """Protocol of a Django 'HttpRequest' object. Abbreviated to the most useful properties."""

    @property
    def GET(self) -> QueryDict:  # noqa: N802
        """A dictionary-like object containing all given HTTP GET parameters."""

    @property
    def POST(self) -> QueryDict:  # noqa: N802
        """A dictionary-like object containing all given HTTP POST parameters."""

    @property
    def COOKIES(self) -> dict[str, str]:  # noqa: N802
        """A dictionary containing all cookies."""

    @property
    def FILES(self) -> MultiValueDict[str, UploadedFile]:  # noqa: N802
        """A dictionary-like object containing all uploaded files."""

    @property
    def META(self) -> dict[str, Any]:  # noqa: N802
        """A dictionary containing all available HTTP headers."""

    @property
    def scheme(self) -> str | None:
        """A string representing the scheme of the request (http or https usually)."""

    @property
    def path(self) -> str:
        """A string representing the full request path, not including the scheme, domain, or query string."""

    @property
    def method(self) -> HttpMethod:
        """A string representing the HTTP method used in the request."""

    @property
    def headers(self) -> HttpHeaders:
        """A case insensitive, dict-like object for accessing headers in the request."""

    @property
    def body(self) -> bytes:
        """The raw HTTP request body as a bytestring."""

    @property
    def encoding(self) -> str | None:
        """A string representing the current encoding used to decode form submission data."""

    @property
    def user(self) -> TUser | AnonymousUser:
        """The user associated with the request."""

    @property
    def session(self) -> SessionBase:
        """A readable and writable, dictionary-like object that represents the current session."""

    @property
    def content_type(self) -> str | None:
        """A string representing the MIME type of the request, parsed from the 'CONTENT_TYPE' header."""

    @property
    def content_params(self) -> dict[str, str] | None:
        """A dictionary of key/value parameters included in the 'CONTENT_TYPE' header."""

    @property
    def accepted_types(self) -> list[MediaType]:
        """A list of 'MediaType' objects representing the accepted content types of the request."""


class DjangoHttpResponseProtocol(Protocol):
    """Protocol of a Django 'HttpResponse' object. Abbreviated to the most useful properties."""

    @property
    def status_code(self) -> int:
        """The status code of the response."""

    @property
    def content(self) -> bytes:
        """The content of the response."""

    @property
    def text(self) -> str:
        """The text of the response."""

    @property
    def headers(self) -> ResponseHeaders:
        """The headers of the response."""

    @property
    def cookies(self) -> SimpleCookie:
        """The cookies of the response."""

    @property
    def charset(self) -> str:
        """The charset of the response."""

    @property
    def streaming(self) -> bool:
        """Whether the response is a streaming response."""


class DjangoTestClientHttpResponseProtocol(DjangoHttpResponseProtocol, Protocol):
    """Protocol of a Django 'HttpResponse' object for testing. Abbreviated to the most useful properties."""

    @property
    def client(self) -> Client:
        """The test client instance."""

    @property
    def request(self) -> dict[str, Any]:
        """The request environment data."""

    @property
    def templates(self) -> list[str]:
        """The list of templates used to render the response."""

    @property
    def context(self) -> dict[str, Any]:
        """The template context used to render the template."""

    def json(self) -> dict[str, Any]:
        """The JSON content of the response."""


class ModelManager(Protocol[TModel]):  # noqa: PLR0904
    """Protocol of a model manager."""

    def get_queryset(self) -> QuerySet[TModel]: ...

    def iterator(self, chunk_size: int | None = None) -> Iterator[TModel]: ...

    def aggregate(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def count(self) -> int: ...

    def get(self, *args: Any, **kwargs: Any) -> TModel: ...

    def create(self, **kwargs: Any) -> TModel: ...

    def bulk_create(  # noqa: PLR0917
        self,
        objs: Iterable[TModel],
        batch_size: int | None = None,
        ignore_conflicts: bool = False,  # noqa: FBT001, FBT002
        update_conflicts: bool = False,  # noqa: FBT001, FBT002
        update_fields: Collection[str] | None = None,
        unique_fields: Collection[str] | None = None,
    ) -> list[TModel]: ...

    def bulk_update(
        self,
        objs: Iterable[TModel],
        fields: Collection[str],
        batch_size: int | None = None,
    ) -> int: ...

    def get_or_create(
        self,
        defaults: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple[TModel, bool]: ...

    def update_or_create(
        self,
        defaults: Mapping[str, Any] | None = None,
        create_defaults: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple[TModel, bool]: ...

    def first(self) -> TModel | None: ...

    def last(self) -> TModel | None: ...

    def delete(self) -> int: ...

    def update(self, **kwargs: Any) -> int: ...

    def exists(self) -> bool: ...

    def contains(self, obj: TModel) -> bool: ...

    def values(self, *fields: str, **expressions: Any) -> QuerySet[TModel]: ...

    def values_list(self, *fields: str, flat: bool = False, named: bool = False) -> QuerySet[TModel]: ...

    def none(self) -> QuerySet[TModel]: ...

    def all(self) -> QuerySet[TModel]: ...

    def filter(self, *args: Any, **kwargs: Any) -> QuerySet[TModel]: ...

    def exclude(self, *args: Any, **kwargs: Any) -> QuerySet[TModel]: ...

    def union(self, *other_qs: QuerySet[TModel], all: bool = False) -> QuerySet[TModel]: ...  # noqa: A002

    def intersection(self, *other_qs: QuerySet[TModel]) -> QuerySet[TModel]: ...

    def difference(self, *other_qs: QuerySet[TModel]) -> QuerySet[TModel]: ...

    def select_related(self, *fields: Any) -> QuerySet[TModel]: ...

    def prefetch_related(self, *lookups: Any) -> QuerySet[TModel]: ...

    def annotate(self, *args: Any, **kwargs: Any) -> QuerySet[TModel]: ...

    def alias(self, *args: Any, **kwargs: Any) -> QuerySet[TModel]: ...

    def order_by(self, *field_names: Any) -> QuerySet[TModel]: ...

    def distinct(self, *field_names: Any) -> QuerySet[TModel]: ...

    def reverse(self) -> QuerySet[TModel]: ...

    def defer(self, *fields: Any) -> QuerySet[TModel]: ...

    def only(self, *fields: Any) -> QuerySet[TModel]: ...

    def using(self, alias: str | None) -> QuerySet[TModel]: ...


class RelatedManager(ModelManager, Protocol[TModel]):
    """Protocol of a manager for one-to-many and many-to-many relations."""

    def add(self, *objs: TModel, bulk: bool = True) -> int: ...

    def set(
        self,
        objs: Iterable[TModel],
        *,
        clear: bool = False,
        through_defaults: Any = None,
    ) -> QuerySet[TModel]: ...

    def clear(self) -> None: ...

    def remove(self, obj: Iterable[TModel], bulk: bool = True) -> TModel: ...  # noqa: FBT001, FBT002

    def create(self, through_defaults: Any = None, **kwargs: Any) -> TModel: ...


# Enums


class RelationType(enum.Enum):
    REVERSE_ONE_TO_ONE = "REVERSE_ONE_TO_ONE"
    FORWARD_ONE_TO_ONE = "FORWARD_ONE_TO_ONE"
    FORWARD_MANY_TO_ONE = "FORWARD_MANY_TO_ONE"
    REVERSE_ONE_TO_MANY = "REVERSE_ONE_TO_MANY"
    REVERSE_MANY_TO_MANY = "REVERSE_MANY_TO_MANY"
    FORWARD_MANY_TO_MANY = "FORWARD_MANY_TO_MANY"
    GENERIC_ONE_TO_MANY = "GENERIC_ONE_TO_MANY"
    GENERIC_MANY_TO_ONE = "GENERIC_MANY_TO_ONE"

    @classmethod
    def for_related_field(cls, field: RelatedField | GenericField) -> RelationType:
        field_cls = type(field)
        try:
            return cls._related_field_to_relation_type_map()[field_cls]
        except KeyError as error:
            msg = f"Unknown related field: {field} (of type {field_cls})"
            raise ValueError(msg) from error

    @enum.property
    def is_reverse(self) -> bool:
        return self in {
            RelationType.REVERSE_ONE_TO_ONE,
            RelationType.REVERSE_ONE_TO_MANY,
            RelationType.REVERSE_MANY_TO_MANY,
        }

    @enum.property
    def is_forward(self) -> bool:
        return self in {
            RelationType.FORWARD_ONE_TO_ONE,
            RelationType.FORWARD_MANY_TO_ONE,
            RelationType.FORWARD_MANY_TO_MANY,
        }

    @enum.property
    def is_generic_relation(self) -> bool:
        return self == RelationType.GENERIC_ONE_TO_MANY

    @enum.property
    def is_generic_foreign_key(self) -> bool:
        return self == RelationType.GENERIC_MANY_TO_ONE

    @classmethod
    @cache
    def _related_field_to_relation_type_map(cls) -> dict[type[RelatedField | GenericField], RelationType]:
        # Must defer creating this map, since the 'contenttypes' app needs to be loaded first.
        from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation  # noqa: PLC0415

        return {
            OneToOneRel: RelationType.REVERSE_ONE_TO_ONE,  # e.g. Reverse OneToOneField
            ManyToOneRel: RelationType.REVERSE_ONE_TO_MANY,
            ManyToManyRel: RelationType.REVERSE_MANY_TO_MANY,  # e.g. Reverse ManyToManyField
            OneToOneField: RelationType.FORWARD_ONE_TO_ONE,
            ForeignKey: RelationType.FORWARD_MANY_TO_ONE,
            ManyToManyField: RelationType.FORWARD_MANY_TO_MANY,
            GenericRelation: RelationType.GENERIC_ONE_TO_MANY,
            GenericForeignKey: RelationType.GENERIC_MANY_TO_ONE,
        }


class MutationKind(enum.StrEnum):
    create = "create"
    update = "update"
    delete = "delete"
    custom = "custom"
    related = "related"

    @enum.property
    def requires_pk(self) -> bool:
        return self in {MutationKind.update, MutationKind.delete}

    @enum.property
    def no_pk(self) -> bool:
        return self == MutationKind.create

    @enum.property
    def should_use_auto(self) -> bool:
        return self in {MutationKind.create, MutationKind.update, MutationKind.custom, MutationKind.related}

    @enum.property
    def should_include_default_value(self) -> bool:
        return self == MutationKind.create


class ManyMatch(enum.StrEnum):
    any = "any"
    all = "all"
    one_of = "one_of"

    @enum.property
    def operator(self) -> Callable[..., Any]:
        match self:
            case ManyMatch.any:
                return op.or_
            case ManyMatch.all:
                return op.and_
            case ManyMatch.one_of:
                return op.xor
            case _:  # pragma: no cover
                msg = f"Unknown operator '{self}'"
                raise ValueError(msg)


# noinspection PyEnum
class UndineErrorCodes(StrEnum):
    """Error codes for Undine errors."""

    @staticmethod
    def _generate_next_value_(name: str, start: Any, count: int, last_values: list[Any]) -> Any:  # noqa: ARG004
        return name

    CONTENT_TYPE_MISSING = auto()
    DUPLICATE_TYPE = auto()
    FIELD_NOT_NULLABLE = auto()
    FILE_NOT_FOUND = auto()
    INVALID_INPUT_DATA = auto()
    INVALID_OPERATION_FOR_METHOD = auto()
    INVALID_ORDER_DATA = auto()
    INVALID_PAGINATION_ARGUMENTS = auto()
    LOOKUP_VALUE_MISSING = auto()
    MISSING_CALCULATION_ARGUMENT = auto()
    MISSING_FILE_MAP = auto()
    MISSING_GRAPHQL_DOCUMENT_PARAMETER = auto()
    MISSING_GRAPHQL_QUERY_AND_DOCUMENT_PARAMETERS = auto()
    MISSING_GRAPHQL_QUERY_PARAMETER = auto()
    MISSING_OPERATION_NAME = auto()
    MISSING_OPERATIONS = auto()
    MODEL_CONSTRAINT_VIOLATION = auto()
    MODEL_NOT_FOUND = auto()
    MUTATION_TOO_MANY_OBJECTS = auto()
    MUTATION_TREE_MODEL_MISMATCH = auto()
    NO_EXECUTION_RESULT = auto()
    NO_OPERATION = auto()
    NODE_ID_NOT_GLOBAL_ID = auto()
    NODE_INTERFACE_MISSING = auto()
    NODE_INVALID_GLOBAL_ID = auto()
    NODE_MISSING_OBJECT_TYPE = auto()
    NODE_QUERY_TYPE_ID_FIELD_MISSING = auto()
    NODE_QUERY_TYPE_MISSING = auto()
    NODE_TYPE_NOT_OBJECT_TYPE = auto()
    OPERATION_NOT_FOUND = auto()
    OPTIMIZER_ERROR = auto()
    PERMISSION_DENIED = auto()
    PERSISTED_DOCUMENT_NOT_FOUND = auto()
    PERSISTED_DOCUMENTS_NOT_SUPPORTED = auto()
    REQUEST_DECODING_ERROR = auto()
    REQUEST_PARSE_ERROR = auto()
    SCALAR_CONVERSION_ERROR = auto()
    SCALAR_INVALID_VALUE = auto()
    SCALAR_TYPE_NOT_SUPPORTED = auto()
    TOO_MANY_FILTERS = auto()
    TOO_MANY_ORDERS = auto()
    UNEXPECTED_ERROR = auto()
    UNION_RESOLVE_TYPE_INVALID_VALUE = auto()
    UNION_RESOLVE_TYPE_MODEL_NOT_FOUND = auto()
    UNSUPPORTED_CONTENT_TYPE = auto()
    VALIDATION_ERROR = auto()


# Model

ToOneField: TypeAlias = OneToOneField | OneToOneRel | ForeignKey
ToManyField: TypeAlias = ManyToManyField | ManyToManyRel | ManyToOneRel
RelatedField: TypeAlias = ToOneField | ToManyField
GenericField: TypeAlias = Union["GenericForeignKey", "GenericRelation", "GenericRel"]
ModelField: TypeAlias = Field | ForeignObjectRel
CombinableExpression: TypeAlias = Expression | Subquery
Annotatable: TypeAlias = CombinableExpression | F | Q
SupportsLookup: TypeAlias = RegisterLookupMixin | type[RegisterLookupMixin]

# GraphQL


class GQLInfo(Generic[TUser], GraphQLResolveInfo):
    """GraphQL execution information given to a GraphQL field resolver."""

    field_name: str
    """Name of the field being resolved."""

    field_nodes: list[FieldNode]
    """
    GraphQL AST Field Nodes in the GraphQL operation for which this field is being resolved for.
    If the same field is queried with a different alias, it will be resolved separately.
    """

    return_type: GraphQLOutputType
    """The GraphQL type of the resolved field."""

    parent_type: GraphQLObjectType
    """The GraphQL type to which this field belongs."""

    path: Path
    """
    Path from the root field to the current field.
    Last part is the field's alias, if one is given, otherwise it's the field's name.
    """

    schema: GraphQLSchema
    """The schema where the GraphQL operation is being executed."""

    fragments: dict[str, FragmentDefinitionNode]
    """A dictionary of GraphQL AST Fragment Definition Nodes in the GraphQL Document."""

    root_value: Any
    """GraphQL root value. Set by `undine_settings.ROOT_VALUE`."""

    operation: OperationDefinitionNode
    """The GraphQL AST Operation Definition Node currently being executed."""

    variable_values: dict[str, Any]
    """The variables passed to the GraphQL operation."""

    context: DjangoRequestProtocol[TUser]
    """The context passed to the GraphQL operation. This is always the Django request object."""

    is_awaitable: Callable[[Any], bool]
    """Function for testing whether the GraphQL resolver is awaitable or not."""


UniquelyNamedGraphQLElement: TypeAlias = (
    GraphQLScalarType
    | GraphQLObjectType
    | GraphQLInterfaceType
    | GraphQLUnionType
    | GraphQLEnumType
    | GraphQLInputObjectType
    | GraphQLDirective
)

Selections: TypeAlias = Iterable[SelectionNode]
ObjectSelections: TypeAlias = Iterable[FieldNode | FragmentSpreadNode]


class NodeDict(Generic[TModel], TypedDict):
    cursor: str
    node: TModel


class PageInfoDict(TypedDict):
    hasNextPage: bool
    hasPreviousPage: bool
    startCursor: str | None
    endCursor: str | None


class ConnectionDict(Generic[TModel], TypedDict):
    totalCount: int
    pageInfo: PageInfoDict
    edges: list[NodeDict[TModel]]


# TypedDicts


class RootTypeParams(TypedDict, total=False):
    """Arguments for an Undine `RootType`."""

    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class EntrypointParams(TypedDict, total=False):
    """Arguments for an Undine `Entrypoint`."""

    many: bool
    nullable: bool
    limit: int
    description: str | None
    deprecation_reason: str | None
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class QueryTypeParams(TypedDict, total=False):
    """Arguments for an Undine `QueryType`."""

    model: type[Model]
    filterset: type[FilterSet]
    orderset: type[OrderSet]
    auto: bool
    exclude: list[str]
    interfaces: list[type[InterfaceType]]
    register: bool
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class FieldParams(TypedDict, total=False):
    """Arguments for an Undine `Field`."""

    many: bool
    nullable: bool
    description: str | None
    deprecation_reason: str | None
    complexity: int
    field_name: str
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class InterfaceTypeParams(TypedDict, total=False):
    """Arguments for an Undine `InterfaceType`."""

    interfaces: list[type[InterfaceType]]
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class InterfaceFieldParams(TypedDict, total=False):
    """Arguments for an Undine `InterfaceField`."""

    args: GraphQLArgumentMap
    resolvable_output_type: bool
    description: str | None
    deprecation_reason: str | None
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class UnionTypeParams(TypedDict, total=False):
    """Arguments for an Undine `UnionType`."""

    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class MutationTypeParams(TypedDict, total=False):
    """Arguments for an Undine `MutationType`."""

    model: type[Model]
    kind: Literal["create", "update", "delete", "custom", "related"]
    auto: bool
    exclude: list[str]
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class InputParams(TypedDict, total=False):
    """Arguments for an Undine `Input`."""

    many: bool
    required: bool
    default_value: DefaultValueType
    input_only: bool
    hidden: bool
    description: str | None
    deprecation_reason: str | None
    field_name: str
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class FilterSetParams(TypedDict, total=False):
    """Arguments for an Undine `FilterSet`."""

    auto: bool
    exclude: list[str]
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class FilterParams(TypedDict, total=False):
    """Arguments for an Undine `Filter`."""

    lookup: str
    many: bool
    match: Literal["any", "all", "one_of"]
    distinct: bool
    required: bool
    description: str | None
    required_aliases: dict[str, DjangoExpression]
    deprecation_reason: str | None
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class OrderSetParams(TypedDict, total=False):
    """Arguments for an Undine `OrderSet`."""

    model: type[Model]
    auto: bool
    exclude: list[str]
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class OrderParams(TypedDict, total=False):
    """Arguments for an Undine `Order`."""

    null_placement: Literal["first", "last"]
    description: str | None
    deprecation_reason: str | None
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class DirectiveParams(TypedDict, total=False):
    """Arguments for an Undine `Directive`."""

    locations: list[DirectiveLocation | str]
    is_repeatable: bool
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class DirectiveArgumentParams(TypedDict, total=False):
    """Arguments for an Undine `DirectiveArgument`."""

    default_value: DefaultValueType
    description: str | None
    deprecation_reason: str | None
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


class CalculationArgumentParams(TypedDict, total=False):
    """Arguments for an Undine `DirectiveArgument`."""

    default_value: DefaultValueType
    description: str | None
    deprecation_reason: str | None
    schema_name: str
    directives: list[Directive]
    extensions: dict[str, Any]


# Resolvers

PermissionFunc: TypeAlias = Callable[[Any, GQLInfo, Any], None]
InputPermFunc: TypeAlias = Callable[[Any, GQLInfo, Any], None]
ValidatorFunc: TypeAlias = Callable[[Any, GQLInfo, Any], None]
OptimizerFunc: TypeAlias = Callable[[Any, "OptimizationData", GQLInfo], None]

GraphQLFilterResolver: TypeAlias = Callable[..., Q]
"""(self: Filter, info: GQLInfo, *, value: Any) -> Q"""

# Callbacks

QuerySetCallback: TypeAlias = Callable[[GQLInfo], QuerySet]
FilterCallback: TypeAlias = Callable[[QuerySet, GQLInfo], QuerySet]


def eval_type(type_: Any, *, globals_: dict[str, Any] | None = None, locals_: dict[str, Any] | None = None) -> Any:
    """
    Evaluate a type, possibly using the given globals and locals.

    This is a proxy of the 'typing._eval_type' function.
    """
    return _eval_type(type_, globals_ or {}, locals_ or {})  # pragma: no cover


# TODO: Subscriptions
# See: https://github.com/enisdenjo/graphql-ws/blob/master/PROTOCOL.md


class ConnectionInitMessage(TypedDict):
    """
    Direction: Client -> Server.

    Indicates that the client wants to establish a connection within the existing socket.
    This connection is not the actual WebSocket communication channel, but is rather a frame
    within it asking the server to allow future operation requests.

    The server must receive the connection initialisation message within the allowed waiting
    time specified in the connectionInitWaitTimeout parameter during the server setup.
    If the client does not request a connection within the allowed timeout, the server will
    close the socket with the event: 4408: Connection initialisation timeout.

    If the server receives more than one ConnectionInit message at any given time, the server
    will close the socket with the event 4429: Too many initialisation requests.

    If the server wishes to reject the connection, for example during authentication,
    it is recommended to close the socket with 4403: Forbidden.
    """

    type: Literal["connection_init"]
    payload: NotRequired[dict[str, Any] | None]


class ConnectionAckMessage(TypedDict):
    """
    Direction: Server -> Client.

    Expected response to the ConnectionInit message from the client acknowledging
    a successful connection with the server.

    The server can use the optional payload field to transfer additional details about the connection.
    """

    type: Literal["connection_ack"]
    payload: NotRequired[dict[str, Any] | None]


class PingMessage(TypedDict):
    """
    Direction: bidirectional.

    Useful for detecting failed connections, displaying latency metrics or other types of network probing.

    A Pong must be sent in response from the receiving party as soon as possible.

    The Ping message can be sent at any time within the established socket.

    The optional payload field can be used to transfer additional details about the ping.
    """

    type: Literal["ping"]
    payload: NotRequired[dict[str, Any] | None]


class PongMessage(TypedDict):
    """
    Direction: bidirectional.

    The response to the Ping message. Must be sent as soon as the Ping message is received.

    The Pong message can be sent at any time within the established socket.
    Furthermore, the Pong message may even be sent unsolicited as an unidirectional heartbeat.

    The optional payload field can be used to transfer additional details about the pong.
    """

    type: Literal["pong"]
    payload: NotRequired[dict[str, Any] | None]


class SubscribeMessagePayload(TypedDict):
    """Payload for the `SubscribeMessage`."""

    operationName: NotRequired[str | None]
    query: str
    variables: NotRequired[dict[str, Any] | None]
    extensions: NotRequired[dict[str, Any] | None]


class SubscribeMessage(TypedDict):
    """
    Direction: Client -> Server.

    Requests an operation specified in the message payload. This message provides a unique ID
    field to connect published messages to the operation requested by this message.

    If there is already an active subscriber for an operation matching the provided ID,
    regardless of the operation type, the server must close the socket immediately with the
    event 4409: Subscriber for <unique-operation-id> already exists.

    The server needs only keep track of IDs for as long as the subscription is active.
    Once a client completes an operation, it is free to re-use that ID.

    Executing operations is allowed only after the server has acknowledged the connection
    through the ConnectionAck message, if the connection is not acknowledged,
    the socket will be closed immediately with the event 4401: Unauthorized.
    """

    id: str
    type: Literal["subscribe"]
    payload: SubscribeMessagePayload


class NextMessagePayload(TypedDict):
    """Payload for the `NextMessage`."""

    errors: NotRequired[list[GraphQLFormattedError]]
    data: NotRequired[dict[str, Any] | None]
    extensions: NotRequired[dict[str, Any]]


class NextMessage(TypedDict):
    """
    Direction: Server -> Client

    Operation execution result(s) from the source stream created by the binding Subscribe message.
    After all results have been emitted, the Complete message will follow indicating stream completion.
    """

    id: str
    type: Literal["next"]
    payload: NextMessagePayload


class ErrorMessage(TypedDict):
    """
    Direction: Server -> Client

    Operation execution error(s) in response to the Subscribe message.
    This can occur before execution starts, usually due to validation errors,
    or during the execution of the request. This message terminates the operation
    and no further messages will be sent.
    """

    id: str
    type: Literal["error"]
    payload: list[GraphQLFormattedError]


class CompleteMessage(TypedDict):
    """
    Direction: bidirectional

    Server -> Client indicates that the requested operation execution has completed.
    If the server dispatched the Error message relative to the original Subscribe message,
    no Complete message will be emitted.

    Client -> Server indicates that the client has stopped listening and wants to complete
    the subscription. No further events, relevant to the original subscription, should be sent through.
    Even if the client sent a Complete message for a single-result-operation before it resolved,
    the result should not be sent through once it does.

    Note: The asynchronous nature of the full-duplex connection means that a client can send
    a Complete message to the server even when messages are in-flight to the client,
    or when the server has itself completed the operation (via a Error or Complete message).
    Both client and server must therefore be prepared to receive (and ignore) messages for
    operations that they consider already completed.
    """

    id: str
    type: Literal["complete"]


Message = (
    ConnectionInitMessage
    | ConnectionAckMessage
    | PingMessage
    | PongMessage
    | SubscribeMessage
    | NextMessage
    | ErrorMessage
    | CompleteMessage
)
