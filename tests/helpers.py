from __future__ import annotations

import contextlib
import dataclasses
import json
import re
from io import BytesIO
from typing import TYPE_CHECKING, Any, Callable, NamedTuple, TypedDict, TypeVar
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpHeaders, HttpRequest, QueryDict
from django.test.client import BOUNDARY
from django.utils.datastructures import MultiValueDict
from graphql import (
    FieldNode,
    FragmentDefinitionNode,
    GraphQLObjectType,
    GraphQLOutputType,
    GraphQLSchema,
    NameNode,
    OperationType,
)
from urllib3 import encode_multipart_formdata
from urllib3.fields import RequestField

from undine.errors.exceptions import UndineError
from undine.optimizer.optimizer import QueryOptimizer

if TYPE_CHECKING:
    from collections.abc import Generator, MutableMapping

    from django.db.models import QuerySet
    from django.http.request import MediaType
    from graphql.pyutils import Path

    from undine.typing import HttpMethod

__all__ = [
    "MockGQLInfo",
    "MockRequest",
    "exact",
    "get_graphql_multipart_spec_request",
    "has",
    "like",
    "parametrize_helper",
]


TNamedTuple = TypeVar("TNamedTuple", bound=NamedTuple)


class ParametrizeArgs(TypedDict):
    argnames: list[str]
    argvalues: list[TNamedTuple]
    ids: list[str]


def parametrize_helper(__tests: dict[str, TNamedTuple], /) -> ParametrizeArgs:
    """Construct parametrize input while setting test IDs."""
    assert __tests, "I need some tests, please!"  # noqa: S101
    values = list(__tests.values())
    try:
        return ParametrizeArgs(
            argnames=list(values[0].__class__.__annotations__),
            argvalues=values,
            ids=list(__tests),
        )
    except AttributeError as error:
        msg = "Improper configuration. Did you use a NamedTuple for TNamedTuple?"
        raise UndineError(msg) from error


class like:  # noqa: N801, PLW1641
    """Compares a string to a regular expression pattern."""

    def __init__(self, query: str) -> None:
        self.pattern: re.Pattern[str] = re.compile(query)

    def __eq__(self, other: str) -> bool:
        if not isinstance(other, str):
            return False
        return self.pattern.match(other) is not None


class has:  # noqa: N801, PLW1641
    """
    Does the compared string contain the specified regular expression patterns?
    Use `str` of `like` objects for "contains" checks, and `bytes` for "excludes" checks.
    """

    def __init__(self, *patterns: str | bytes | like) -> None:
        self.patterns = patterns

    def __eq__(self, other: str) -> bool:
        if not isinstance(other, str):
            return NotImplemented
        return all(
            pattern.decode() not in other if isinstance(pattern, bytes) else pattern in other
            for pattern in self.patterns
        )


def exact(msg: str) -> str:
    """Use in `with pytest.raises(..., match=exact(msg))` to match the 'msg' string exactly."""
    return f"^{re.escape(msg)}$"


def get_graphql_multipart_spec_request(
    op: dict[str, Any] | str | None = ...,
    op_map: dict[str, Any] | str | None = ...,
    file: bytes | None = ...,
) -> HttpRequest:
    """Get a mock HTTPRequest conforming to the GraphQL multipart spec."""
    fields: list[RequestField] = []

    if op is ...:
        op = {"query": "mutation($file: File!) { files(files: $file) { id } }", "variables": {"file": None}}
    if op is not None:
        fields.append(
            RequestField(
                name="operations",
                data=json.dumps(op),
                headers={"Content-Disposition": 'form-data; name="operations"'},
            ),
        )

    if op_map is ...:
        op_map = {"0": ["variables.file"]}
    if op_map is not None:
        fields.append(
            RequestField(
                name="map",
                data=json.dumps(op_map),
                headers={"Content-Disposition": 'form-data; name="map"'},
            ),
        )

    if file is ...:
        file = (
            # A black pixel.
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15\xc4\x89\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x04gAMA\x00\x00\xb1"
            b"\x8f\x0b\xfca\x05\x00\x00\x00\tpHYs\x00\x00\x0e\xc3\x00\x00\x0e\xc3\x01\xc7o\xa8d\x00\x00"
            b"\x00\rIDAT\x18Wc```\xf8\x0f\x00\x01\x04\x01\x00p e\x0b\x00\x00\x00\x00IEND\xaeB`\x82"
        )
    if file is not None:
        fields.append(
            RequestField(
                name="0",
                data=file,
                filename="image.jpg",
                headers={"Content-Disposition": 'form-data; name="0"; filename="image.png"'},
            ),
        )

    data, content_type = encode_multipart_formdata(fields, boundary=BOUNDARY)

    request = HttpRequest()
    request._stream = BytesIO(data)  # noqa: SLF001
    request._read_started = False  # noqa: SLF001
    request.content_type = "multipart/form-data"
    request.META["CONTENT_TYPE"] = content_type
    request.META["CONTENT_LENGTH"] = str(len(data))
    request.method = "POST"
    request.encoding = "utf-8"
    request._load_post_and_files()  # noqa: SLF001
    request.POST = request._post  # noqa: SLF001
    request.FILES = request._files  # noqa: SLF001
    return request


@dataclasses.dataclass(kw_only=True)
class MockRequest:
    path: str = "/"
    method: HttpMethod = "GET"
    body: bytes = b""
    encoding: str = "utf-8"
    user: User | AnonymousUser = dataclasses.field(default_factory=AnonymousUser)
    session: MutableMapping[str, Any] = dataclasses.field(default_factory=dict)
    accepted_types: list[MediaType] = dataclasses.field(default_factory=list)
    headers: HttpHeaders = dataclasses.field(default_factory=dict)
    scheme: str = "http"
    content_type: str = "application/json"
    GET: QueryDict = dataclasses.field(default_factory=lambda: QueryDict(mutable=True))
    POST: QueryDict = dataclasses.field(default_factory=lambda: QueryDict(mutable=True))
    COOKIES: dict[str, Any] = dataclasses.field(default_factory=dict)
    META: dict[str, Any] = dataclasses.field(default_factory=dict)
    FILES: MultiValueDict = dataclasses.field(default_factory=MultiValueDict)


def _default_field_nodes() -> list[FieldNode]:
    return [
        FieldNode(
            loc=None,
            directives=(),
            alias=None,
            name=NameNode(value=""),
            arguments=(),
            selection_set=None,
        ),
    ]


@dataclasses.dataclass(kw_only=True)
class MockGQLInfo:
    field_name: str = ""
    field_nodes: list[FieldNode] = dataclasses.field(default_factory=_default_field_nodes)
    return_type: GraphQLOutputType | None = None
    parent_type: GraphQLObjectType | None = None
    path: Path | None = None
    schema: GraphQLSchema | None = None
    fragments: dict[str, FragmentDefinitionNode] = dataclasses.field(default_factory=dict)
    root_value: Any | None = None
    operation: OperationType = OperationType.QUERY
    variable_values: dict[str, Any] = dataclasses.field(default_factory=dict)
    context: Any = dataclasses.field(default_factory=MockRequest)


@contextlib.contextmanager
def patch_optimizer(*, func: Callable[[QuerySet], QuerySet] | None = None) -> Generator[None, None, None]:
    """Skip QueryOptimizer's optimization step when this patch is active."""
    if func is None:

        def func(qs: QuerySet) -> QuerySet:
            return qs

    path = QueryOptimizer.__module__ + "." + QueryOptimizer.__qualname__ + "." + QueryOptimizer.optimize.__name__
    with patch(path, side_effect=func):
        yield
