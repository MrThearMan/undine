from __future__ import annotations

import enum
import operator as op
from collections import defaultdict
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from enum import Enum, StrEnum, auto
from functools import cache
from types import FunctionType, GenericAlias, UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
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
    ExecutionResult,
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
from graphql.pyutils import AwaitableOrValue

if TYPE_CHECKING:
    from http.cookies import SimpleCookie

    from asgiref.typing import ASGISendEvent
    from django.contrib.auth.models import AbstractUser, AnonymousUser, User
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
        FormattedExecutionResult,
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
    from undine.utils.graphql.websocket import WebSocketRequest

__all__ = [
    "Annotatable",
    "CalculationArgumentParams",
    "ClientMessage",
    "CombinableExpression",
    "CompleteMessage",
    "ConnectionAckMessage",
    "ConnectionDict",
    "ConnectionInitMessage",
    "DirectiveArgumentParams",
    "DirectiveParams",
    "DispatchProtocol",
    "DjangoExpression",
    "DjangoRequestProtocol",
    "DjangoResponseProtocol",
    "DjangoTestClientResponseProtocol",
    "DocstringParserProtocol",
    "EntrypointParams",
    "ErrorMessage",
    "ExecutionResultGen",
    "FieldParams",
    "FieldPermFunc",
    "FilterAliasesFunc",
    "FilterParams",
    "FilterSetParams",
    "GQLInfo",
    "GraphQLFilterResolver",
    "InputParams",
    "InputPermFunc",
    "InterfaceFieldParams",
    "InterfaceTypeParams",
    "JsonObject",
    "Lambda",
    "LiteralArg",
    "ManyMatch",
    "ModelField",
    "MutationKind",
    "MutationTypeParams",
    "NextMessage",
    "NodeDict",
    "ObjectSelections",
    "OptimizerFunc",
    "OrderAliasesFunc",
    "OrderParams",
    "OrderSetParams",
    "PageInfoDict",
    "ParametrizedType",
    "PingMessage",
    "PongMessage",
    "ProtocolType",
    "QueryTypeParams",
    "RelatedField",
    "RequestMethod",
    "RootTypeParams",
    "Selections",
    "Self",
    "ServerMessage",
    "SubscribeMessage",
    "SupportsLookup",
    "ToManyField",
    "ToOneField",
    "UndineErrorCodes",
    "UnionTypeParams",
    "ValidatorFunc",
    "WebSocketConnectionInitHook",
    "WebSocketConnectionPingHook",
    "WebSocketConnectionPongHook",
    "WebSocketProtocol",
    "WebSocketResult",
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
WebSocketResult: TypeAlias = AsyncIterator[ExecutionResult] | ExecutionResult
ExecutionResultGen: TypeAlias = AsyncGenerator[ExecutionResult, None]

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

RequestMethod: TypeAlias = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "HEAD", "WEBSOCKET"]

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


class DjangoRequestProtocol(Protocol[TUser]):  # noqa: PLR0904
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
    def method(self) -> RequestMethod:
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

    async def auser(self) -> TUser | AnonymousUser:
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

    @property
    def response_content_type(self) -> str:
        """Response content type as determined from 'accepted_types' in relation to the endpoint's supported types."""

    @response_content_type.setter
    def response_content_type(self, value: str) -> None:
        """Set by decorators in 'undine.http.utils'."""

    def is_secure(self) -> bool:
        """A boolean representing whether the request is over HTTPS."""

    def accepts(self, media_type: str) -> bool:
        """Does the client accept a response in the given media type?"""

    def get_host(self) -> str:
        """Return the HTTP host using the environment or request headers."""

    def get_port(self) -> str:
        """Return the port number for the request as a string."""

    def get_full_path(self, force_append_slash: bool = False) -> str:  # noqa: FBT001,FBT002
        """Return the full path for the request."""

    def get_full_path_info(self, force_append_slash: bool = False) -> str:  # noqa: FBT001,FBT002
        """Return the full path info for the request."""

    def build_absolute_uri(self, location: str | None = None) -> str:
        """Build an absolute URI from the location and the variables available in this request."""


class DjangoResponseProtocol(Protocol):
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


class DjangoTestClientResponseProtocol(DjangoResponseProtocol, Protocol):
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
    def should_use_autogeneration(self) -> bool:
        return self in {MutationKind.create, MutationKind.update, MutationKind.related}

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

    ASYNC_NOT_SUPPORTED = auto()
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
    MISSING_INSTANCES_TO_DELETE = auto()
    MISSING_OPERATION_NAME = auto()
    MISSING_OPERATIONS = auto()
    MISSING_SUBSCRIPTION_ARGUMENT = auto()
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
    UNEXPECTED_CALCULATION_ARGUMENT = auto()
    UNEXPECTED_ERROR = auto()
    UNEXPECTED_SUBSCRIPTION_ARGUMENT = auto()
    UNION_RESOLVE_TYPE_INVALID_VALUE = auto()
    UNION_RESOLVE_TYPE_MODEL_NOT_FOUND = auto()
    UNSUPPORTED_CONTENT_TYPE = auto()
    USE_WEBSOCKETS_FOR_SUBSCRIPTIONS = auto()
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


class PostgresFTSLangSpecificFields(TypedDict, total=False):
    """Specify fields for text search per language."""

    # Cannot use "Iterable[str]" since "str" is also an iterable of strings.
    arabic: list[str] | tuple[str, ...] | set[str]
    armenian: list[str] | tuple[str, ...] | set[str]
    basque: list[str] | tuple[str, ...] | set[str]
    catalan: list[str] | tuple[str, ...] | set[str]
    danish: list[str] | tuple[str, ...] | set[str]
    dutch: list[str] | tuple[str, ...] | set[str]
    english: list[str] | tuple[str, ...] | set[str]
    finnish: list[str] | tuple[str, ...] | set[str]
    french: list[str] | tuple[str, ...] | set[str]
    german: list[str] | tuple[str, ...] | set[str]
    greek: list[str] | tuple[str, ...] | set[str]
    hindi: list[str] | tuple[str, ...] | set[str]
    hungarian: list[str] | tuple[str, ...] | set[str]
    indonesian: list[str] | tuple[str, ...] | set[str]
    irish: list[str] | tuple[str, ...] | set[str]
    italian: list[str] | tuple[str, ...] | set[str]
    lithuanian: list[str] | tuple[str, ...] | set[str]
    nepali: list[str] | tuple[str, ...] | set[str]
    norwegian: list[str] | tuple[str, ...] | set[str]
    portuguese: list[str] | tuple[str, ...] | set[str]
    romanian: list[str] | tuple[str, ...] | set[str]
    russian: list[str] | tuple[str, ...] | set[str]
    serbian: list[str] | tuple[str, ...] | set[str]
    spanish: list[str] | tuple[str, ...] | set[str]
    swedish: list[str] | tuple[str, ...] | set[str]
    tamil: list[str] | tuple[str, ...] | set[str]
    turkish: list[str] | tuple[str, ...] | set[str]
    yiddish: list[str] | tuple[str, ...] | set[str]


FTSLang: TypeAlias = Literal[
    "arabic",
    "armenian",
    "basque",
    "catalan",
    "danish",
    "dutch",
    "english",
    "finnish",
    "french",
    "german",
    "greek",
    "hindi",
    "hungarian",
    "indonesian",
    "irish",
    "italian",
    "lithuanian",
    "nepali",
    "norwegian",
    "portuguese",
    "romanian",
    "russian",
    "serbian",
    "spanish",
    "swedish",
    "tamil",
    "turkish",
    "yiddish",
]

LangCode: TypeAlias = Literal[
    "ar",
    "hy",
    "eu",
    "ca",
    "da",
    "nl",
    "en",
    "fi",
    "fr",
    "de",
    "el",
    "hi",
    "hu",
    "id",
    "ga",
    "it",
    "lt",
    "ne",
    "nb",
    "pt",
    "ro",
    "ru",
    "sr",
    "es",
    "sv",
    "ta",
    "tr",
    "yi",
]

LangSep: TypeAlias = Literal["|", "&", "<->", "<1>", "<2>", "<3>", "<4>", "<5>", "<6>", "<7>", "<8>", "<9>"]


# Resolvers

_AnyValue: TypeAlias = Annotated[Any, "value"]
_AnyModel: TypeAlias = Annotated[Any, "django.db.models.Model"]
_AnyField: TypeAlias = Annotated[Any, "undine.Field"]
_AnyFilter: TypeAlias = Annotated[Any, "undine.Filter"]
_AnyOrder: TypeAlias = Annotated[Any, "undine.Order"]

FieldPermFunc: TypeAlias = Callable[[_AnyModel, GQLInfo, _AnyValue], None]
InputPermFunc: TypeAlias = Callable[[_AnyModel, GQLInfo, _AnyValue], None]
ValidatorFunc: TypeAlias = Callable[[_AnyModel, GQLInfo, _AnyValue], None]

OptimizerFunc: TypeAlias = Callable[[_AnyField, "OptimizationData", GQLInfo], None]


class FilterAliasesFunc(Protocol):
    def __call__(self, root: _AnyFilter, /, info: GQLInfo, *, value: Any) -> dict[str, DjangoExpression]: ...


class OrderAliasesFunc(Protocol):
    def __call__(self, root: _AnyOrder, /, info: GQLInfo, *, descending: bool) -> dict[str, DjangoExpression]: ...


class GraphQLFilterResolver(Protocol):
    def __call__(self, root: _AnyFilter, /, info: GQLInfo, *, value: Any) -> Q: ...


# Callbacks

QuerySetCallback: TypeAlias = Callable[[GQLInfo], QuerySet]
FilterCallback: TypeAlias = Callable[[QuerySet, GQLInfo], QuerySet]
PersistedDocumentsPermissionsCallback: TypeAlias = Callable[[DjangoRequestProtocol, dict[str, str]], None]


def eval_type(type_: Any, *, globals_: dict[str, Any] | None = None, locals_: dict[str, Any] | None = None) -> Any:
    """
    Evaluate a type, possibly using the given globals and locals.

    This is a proxy of the 'typing._eval_type' function.
    """
    return _eval_type(type_, globals_ or {}, locals_ or {})  # pragma: no cover


# Subscriptions


class ConnectionInitMessage(TypedDict):
    type: Literal["connection_init"]
    payload: NotRequired[dict[str, Any] | None]


class ConnectionAckMessage(TypedDict):
    type: Literal["connection_ack"]
    payload: NotRequired[dict[str, Any] | None]


class PingMessage(TypedDict):
    type: Literal["ping"]
    payload: NotRequired[dict[str, Any] | None]


class PongMessage(TypedDict):
    type: Literal["pong"]
    payload: NotRequired[dict[str, Any] | None]


class SubscribeMessage(TypedDict):
    type: Literal["subscribe"]
    id: str
    payload: dict[str, Any]  # GraphQL operation params


class NextMessage(TypedDict):
    type: Literal["next"]
    id: str
    payload: FormattedExecutionResult


class ErrorMessage(TypedDict):
    type: Literal["error"]
    id: str
    payload: list[GraphQLFormattedError]


class CompleteMessage(TypedDict):
    type: Literal["complete"]
    id: str


ClientMessage: TypeAlias = ConnectionInitMessage | PingMessage | PongMessage | SubscribeMessage | CompleteMessage
"""Messages sent by the client."""

ServerMessage: TypeAlias = (
    ConnectionAckMessage | PingMessage | PongMessage | NextMessage | ErrorMessage | CompleteMessage
)
"""Messages sent by the server."""


class UrlRoute(TypedDict):
    args: tuple[str, ...]
    kwargs: dict[str, str]


class WebSocketASGIScope(TypedDict):
    type: str
    asgi: dict[str, str]
    http_version: str
    scheme: str
    server: tuple[str, int]
    client: tuple[str, int]
    root_path: str
    path: str
    raw_path: bytes
    query_string: bytes
    headers: list[tuple[bytes, bytes]]
    subprotocols: list[str]
    state: dict[str, Any]
    extensions: dict[str, Any]
    cookies: dict[str, str]
    session: SessionBase
    user: User | AnonymousUser
    path_remaining: str
    url_route: UrlRoute


class GraphQLWebSocketCloseCode(enum.IntEnum):
    """Possible WebSocket close codes."""

    # WebSocket Protocol.
    # See: https://datatracker.ietf.org/doc/html/rfc6455#section-7.4.1

    NORMAL_CLOSURE = 1000
    """Client has closed the connection normally."""

    GOING_AWAY = 1001
    """Browser tab closing, graceful server shutdown."""

    PROTOCOL_ERROR = 1002
    """Endpoint received malformed frame."""

    UNSUPPORTED_DATA = 1003
    """Endpoint received unsupported frame."""

    NO_STATUS_RCVD = 1005
    """Got no close status but transport layer finished normally."""

    ABNORMAL_CLOSURE = 1006
    """Transport layer broke."""

    INVALID_FRAME_PAYLOAD_DATA = 1007
    """Data in endpoint's frame is not consistent."""

    POLICY_VIOLATION = 1008
    """Generic code not applicable to any other."""

    MESSAGE_TOO_BIG = 1009
    """Endpoint won't process large message."""

    MANDATORY_EXTENSION = 1010
    """Client wanted extension(s) that server did not negotiate."""

    INTERNAL_ERROR = 1011
    """Unexpected server problem while operating."""

    SERVICE_RESTART = 1012
    """Server/service is restarting."""

    TRY_AGAIN_LATER = 1013
    """Temporary server condition forced blocking client's application-based request."""

    BAD_GATEWAY = 1014
    """Server acting as gateway/proxy got invalid response."""

    TLS_HANDSHAKE = 1015
    """Transport layer broke because TLS handshake failed."""

    # GraphQL over WebSocket Protocol.
    # See: https://github.com/graphql/graphql-over-http/blob/main/rfcs/GraphQLOverWebSocket.md

    BAD_REQUEST = 4400
    """Client has sent and invalid message to the Server."""

    UNAUTHORIZED = 4401
    """Client has not received a ConnectionAck response before attempting to sent a Subscribe message."""

    FORBIDDEN = 4403
    """Server has rejected the connection init attempt."""

    BAD_RESPONSE = 4004
    """Client received an invalid message from the Server."""

    INTERNAL_CLIENT_ERROR = 4005
    """An unexpected error occurred on the Client."""

    SUBPROTOCOL_NOT_ACCEPTABLE = 4406
    """Server does not support the websocket sub-protocol requested by the Client."""

    CONNECTION_INITIALISATION_TIMEOUT = 4408
    """Server did not receive a valid ConnectionInit message from the Client in the specified time."""

    SUBSCRIBER_ALREADY_EXISTS = 4409
    """A Subscribe operation already exists for the ID given by the Client."""

    TOO_MANY_INITIALISATION_REQUESTS = 4429
    """More than one ConnectionInit request made by the Client."""

    INTERNAL_SERVER_ERROR = 4500
    """An unexpected error occurred on the Server."""

    CONNECTION_ACKNOWLEDGEMENT_TIMEOUT = 4504
    """Server did not send the ConnectionAck message to the Client in the specified time."""


WebSocketConnectionInitHook: TypeAlias = Callable[["WebSocketRequest"], AwaitableOrValue[dict[str, Any] | None]]
WebSocketConnectionPingHook: TypeAlias = Callable[["WebSocketRequest"], AwaitableOrValue[dict[str, Any] | None]]
WebSocketConnectionPongHook: TypeAlias = Callable[["WebSocketRequest"], AwaitableOrValue[None]]


class WebSocketProtocol(Protocol):
    @property
    def scope(self) -> WebSocketASGIScope: ...

    async def send(self, message: ASGISendEvent) -> None: ...
