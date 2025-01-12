from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, MutableMapping
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    NewType,
    NotRequired,
    Protocol,
    Self,
    TypeAlias,
    TypedDict,
    TypeVar,
    Union,
    runtime_checkable,
)

from graphql import GraphQLFormattedError

# Sort separately due to being a private import
from typing import _eval_type  # isort: skip  # noqa: PLC2701  # type: ignore[attr-defined]
from typing import _GenericAlias  # isort: skip  # noqa: PLC2701  # type: ignore[attr-defined]
from typing import _TypedDictMeta  # isort: skip  # noqa: PLC2701  # type: ignore[attr-defined]

from django.core.handlers.wsgi import WSGIRequest
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
from graphql import FieldNode, GraphQLInputType, GraphQLOutputType, GraphQLResolveInfo, GraphQLType, SelectionNode

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation
    from django.contrib.sessions.backends.base import SessionBase
    from django.db.models.sql import Query

    from undine import Field as UndineField
    from undine import Input, MutationType, QueryType
    from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion, TypeRef
    from undine.optimizer.optimizer import OptimizationData
    from undine.relay import Connection, Node

__all__ = [
    "CalculationResolver",
    "CombinableExpression",
    "CompleteMessage",
    "ConnectionAckMessage",
    "ConnectionDict",
    "ConnectionInitMessage",
    "DispatchCategory",
    "DispatchProtocol",
    "DispatchWrapper",
    "DjangoRequestProtocol",
    "DocstringParserProtocol",
    "EntrypointRef",
    "ErrorMessage",
    "ExpressionLike",
    "FieldPermFunc",
    "FieldRef",
    "FilterRef",
    "GQLInfo",
    "GraphQLFilterResolver",
    "HttpMethod",
    "InputPermFunc",
    "InputRef",
    "JsonObject",
    "Lambda",
    "LiteralArg",
    "Message",
    "ModelField",
    "ModelManager",
    "MutationKind",
    "NextMessage",
    "NextMessagePayload",
    "NodeDict",
    "OptimizerFunc",
    "OrderRef",
    "PageInfoDict",
    "ParametrizedType",
    "PingMessage",
    "PongMessage",
    "RelatedField",
    "RelatedManager",
    "Root",
    "Selections",
    "Self",
    "SubscribeMessage",
    "SubscribeMessagePayload",
    "ToManyField",
    "ToOneField",
    "ValidatorFunc",
]

# Misc.

TypedDictType: TypeAlias = _TypedDictMeta
ParametrizedType: TypeAlias = _GenericAlias
JsonObject: TypeAlias = dict[str, Any] | list["JsonObject"]
PrefetchHackCacheType: TypeAlias = defaultdict[str, defaultdict[str, set[str]]]
LiteralArg: TypeAlias = str | int | bytes | bool | Enum | None

# TypeVars

From = TypeVar("From")
To = TypeVar("To")
TModel = TypeVar("TModel", bound=Model)
TGraphQLType = TypeVar("TGraphQLType", GraphQLInputType, GraphQLOutputType)
TTypedDict = TypeVar("TTypedDict", bound=TypedDictType)

# Literals

MutationKind: TypeAlias = Literal["create", "update", "delete", "custom", "nested"]
HttpMethod: TypeAlias = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "HEAD"]
DispatchCategory: TypeAlias = Literal["types", "instances", "literals", "protocols"]

# NewTypes

Lambda = NewType("Lambda", Callable)
"""
Type used to regiser a different implementations for lambda functions
as opposed to a regular function in the FunctionDispatcher.
"""

empty = object()


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


class ExpressionLike(Protocol):
    def resolve_expression(
        self,
        query: Query,
        allow_joins: bool,  # noqa: FBT001
        reuse: set[str] | None,
        summarize: bool,  # noqa: FBT001
        for_save: bool,  # noqa: FBT001
    ) -> ExpressionLike: ...


class DispatchProtocol(Protocol[From, To]):
    def __call__(self, key: From, **kwargs: Any) -> To: ...


DispatchWrapper: TypeAlias = Callable[[DispatchProtocol[From, To]], DispatchProtocol[From, To]]


class DjangoRequestProtocol(Protocol):
    @property
    def user(self) -> User | AnonymousUser: ...

    @property
    def session(self) -> SessionBase | MutableMapping[str, Any]: ...


class GQLInfoProtocol(Protocol):
    @property
    def context(self) -> DjangoRequestProtocol: ...


class ModelManager(Protocol[TModel]):  # noqa: PLR0904
    """Represents a manager for a model."""

    def get_queryset(self) -> QuerySet[TModel]: ...

    def iterator(self, chunk_size: int | None = None) -> Iterator[TModel]: ...

    def aggregate(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def count(self) -> int: ...

    def get(self, *args: Any, **kwargs: Any) -> TModel: ...

    def create(self, **kwargs: Any) -> TModel: ...

    def bulk_create(
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


class RelatedManager(ModelManager[TModel]):
    """Represents a manager for one-to-many and many-to-many relations."""

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


# Model

ToOneField: TypeAlias = OneToOneField | OneToOneRel | ForeignKey
ToManyField: TypeAlias = ManyToManyField | ManyToManyRel | ManyToOneRel
RelatedField: TypeAlias = ToOneField | ToManyField
GenericField: TypeAlias = Union["GenericForeignKey", "GenericRelation", "GenericRel"]
ModelField: TypeAlias = Field | ForeignObjectRel
CombinableExpression: TypeAlias = Expression | Subquery
QueryResult: TypeAlias = Model | list[Model] | None
MutationResult: TypeAlias = Model | list[Model] | None
DjangoRequest: TypeAlias = WSGIRequest | DjangoRequestProtocol

# GraphQL

Root: TypeAlias = Any
GQLInfo: TypeAlias = GQLInfoProtocol | GraphQLResolveInfo
GraphQLInputOutputType: TypeAlias = GraphQLOutputType | GraphQLInputType
Selections: TypeAlias = Iterable[SelectionNode | FieldNode]
GraphQLIOType: TypeAlias = GraphQLInputType | GraphQLOutputType


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


# Resolvers

ValidatorFunc: TypeAlias = Callable[["Input", GQLInfo, Any], None]
OptimizerFunc: TypeAlias = Callable[["UndineField", "OptimizationData"], None]
FieldPermFunc: TypeAlias = Callable[["UndineField", GQLInfo, Model], None]
InputPermFunc: TypeAlias = Callable[["Input", GQLInfo, Any], None]

GraphQLFilterResolver: TypeAlias = Callable[..., Q]
"""(self: Model, info: GQLInfo, **kwargs: Any) -> Q"""

CalculationResolver: TypeAlias = Callable[..., QuerySet]
"""(self: Field, queryset: QuerySet, info: GQLInfo, **kwargs: Any) -> QuerySet"""

# Callbacks

QuerySetCallback: TypeAlias = Callable[[GQLInfo], QuerySet]
FilterCallback: TypeAlias = Callable[[QuerySet, GQLInfo], QuerySet]

# Refs

EntrypointRef: TypeAlias = Union[
    type["QueryType"],
    type["MutationType"],
    "Node",
    "Connection",
    Callable[..., Any],
]
FieldRef: TypeAlias = Union[
    Field,
    ForeignObjectRel,
    type["QueryType"],
    "LazyQueryType",
    "LazyQueryTypeUnion",
    "LazyLambdaQueryType",
    Expression,
    Subquery,
    GraphQLType,
    "TypeRef",
    "Connection",
    "Calculated",
    Callable[..., Any],
]
FilterRef: TypeAlias = Field | ForeignObjectRel | Q | Expression | Subquery | Callable[..., Any]
OrderRef: TypeAlias = F | Expression | Subquery
InputRef: TypeAlias = Union[
    Field,
    type["MutationType"],
    "TypeRef",
    Callable[..., Any],
]


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
