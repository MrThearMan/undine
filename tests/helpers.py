from __future__ import annotations

import base64
import dataclasses
import json
import re
from contextlib import contextmanager
from io import BytesIO
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict, TypeVar
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.base import SessionBase
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.uploadhandler import MemoryFileUploadHandler
from django.http import HttpHeaders, QueryDict
from django.http.multipartparser import MultiPartParser
from django.http.request import MediaType
from django.test.client import BOUNDARY
from django.utils.datastructures import MultiValueDict
from graphql import FieldNode, GraphQLObjectType, GraphQLScalarType, NameNode, OperationDefinitionNode, Undefined
from graphql.pyutils import Path
from urllib3 import encode_multipart_formdata
from urllib3.fields import RequestField

from undine.exceptions import UndineError
from undine.optimizer.optimizer import OptimizationResults, QueryOptimizer
from undine.settings import example_schema, undine_settings
from undine.typing import GQLInfo

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from django.contrib.auth.models import User
    from django.core.files.uploadedfile import UploadedFile
    from graphql import FragmentDefinitionNode, GraphQLOutputType, GraphQLSchema

    from undine.typing import HttpMethod

__all__ = [
    "MockRequest",
    "create_graphql_multipart_spec_request",
    "exact",
    "mock_gql_info",
    "parametrize_helper",
]


TNamedTuple = TypeVar("TNamedTuple", bound=NamedTuple)

PNG = base64.b64decode(b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4AWNgYGAAAAAEAAHklIQGAAAAAElFTkSuQmCC")
"""A single blank pixel PNG image in base64 encoding."""


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


def exact(msg: str) -> str:
    """Use in `with pytest.raises(..., match=exact(msg))` to match the 'msg' string exactly."""
    return f"^{re.escape(msg)}$"


def create_graphql_multipart_spec_request(
    *,
    operations: dict[str, Any] | Any = Undefined,
    operations_map: dict[str, list[str]] | Any = Undefined,
    files: dict[str, SimpleUploadedFile] | Any = Undefined,
) -> MockRequest:
    """Get a mock HTTPRequest conforming to the GraphQL multipart spec."""
    data: dict[str, str | bytes] = {}

    if operations is Undefined:
        operations = {
            "query": "mutation($file: File!) { files(files: $file) { id } }",
            "variables": {"file": None},
        }

    if operations is not None:
        data["operations"] = json.dumps(operations)

    if operations_map is Undefined:
        operations_map = {
            "0": ["variables.file"],
        }

    if operations_map is not None:
        data["map"] = json.dumps(operations_map)

    if files is Undefined:
        files = {
            "0": SimpleUploadedFile("image.png", PNG, content_type="image/png"),
        }

    return create_multipart_form_data_request(data=data, files=files)


def create_multipart_form_data_request(
    *,
    data: dict[str, str | bytes],
    files: dict[str, SimpleUploadedFile] | None = None,
) -> MockRequest:
    """Create a MockRequest object for a multipart/form-data request."""
    fields: list[RequestField] = [
        RequestField(
            name=key,
            data=value,
            headers={"Content-Disposition": f'form-data; name="{key}"'},
        )
        for key, value in data.items()
    ]

    if files is not None:
        fields += [
            RequestField(
                name=name,
                data=file.file.read(),
                filename=file.name,
                headers={"Content-Disposition": f'form-data; name="{name}"; filename="{file.name}"'},
            )
            for name, file in files.items()
            if file.file is not None and file.name is not None
        ]

    body, content_type = encode_multipart_formdata(fields, boundary=BOUNDARY)

    encoding = "utf-8"
    headers = {"CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(len(body))}

    parser = MultiPartParser(
        META=headers,
        input_data=BytesIO(body),
        upload_handlers=[MemoryFileUploadHandler()],
        encoding=encoding,
    )

    post, files = parser.parse()

    return MockRequest(
        method="POST",
        accepted_types=[MediaType("application/json")],
        content_type=content_type,
        encoding=encoding,
        body=body,
        POST=post,
        META=headers,
        FILES=files,
        headers=HttpHeaders(headers),
    )


@dataclasses.dataclass(kw_only=True)
class MockRequest:
    GET: QueryDict = dataclasses.field(default_factory=lambda: QueryDict(mutable=True))
    POST: QueryDict = dataclasses.field(default_factory=lambda: QueryDict(mutable=True))
    COOKIES: dict[str, Any] = dataclasses.field(default_factory=dict)
    FILES: MultiValueDict[str, UploadedFile] = dataclasses.field(default_factory=MultiValueDict)
    META: dict[str, Any] = dataclasses.field(default_factory=dict)
    scheme: str = "http"
    path: str = "/"
    method: HttpMethod = "GET"
    headers: HttpHeaders = dataclasses.field(default_factory=lambda: HttpHeaders({}))
    body: bytes = b""
    encoding: str | None = "utf-8"
    user: User | AnonymousUser = dataclasses.field(default_factory=AnonymousUser)
    session: SessionBase = dataclasses.field(default_factory=SessionBase)
    content_type: str | None = "application/json"
    content_params: dict[str, str] | None = dataclasses.field(default_factory=dict)
    accepted_types: list[MediaType] = dataclasses.field(default_factory=list)

    async def auser(self) -> User:
        return self.user


def mock_gql_info(  # noqa: PLR0913
    *,
    field_name: str | None = None,
    field_nodes: list[FieldNode] | None = None,
    return_type: GraphQLOutputType | None = None,
    parent_type: GraphQLObjectType | None = None,
    path: Path | None = None,
    schema: GraphQLSchema | None = None,
    fragments: dict[str, FragmentDefinitionNode] | None = None,
    root_value: Any | None = None,
    operation: OperationDefinitionNode | None = None,
    variable_values: dict[str, Any] | None = None,
    context: Any | None = None,
    is_awaitable: Callable[[Any], bool] | None = None,
) -> GQLInfo:
    """Create a GraphQL resolve info object for testing purposes."""
    _default_field_nodes = [
        FieldNode(
            loc=None,
            directives=(),
            alias=None,
            name=NameNode(value=""),
            arguments=(),
            selection_set=None,
        ),
    ]

    return GQLInfo(
        field_name="" if field_name is None else field_name,
        field_nodes=_default_field_nodes if field_nodes is None else field_nodes,
        return_type=GraphQLScalarType(name="return") if return_type is None else return_type,
        parent_type=GraphQLObjectType(name="parent", fields={}) if parent_type is None else parent_type,
        path=Path(prev=None, key="", typename="") if path is None else path,
        schema=example_schema if schema is None else schema,
        fragments={} if fragments is None else fragments,
        root_value=undine_settings.ROOT_VALUE if root_value is None else root_value,
        operation=OperationDefinitionNode() if operation is None else operation,
        variable_values={} if variable_values is None else variable_values,
        context=MockRequest() if context is None else context,
        is_awaitable=(lambda _: False) if is_awaitable is None else is_awaitable,
    )


@contextmanager
def patch_optimizer(**kwargs: Any) -> Generator[None, None, None]:
    """Skip QueryOptimizer when this patch is active."""
    path = QueryOptimizer.__module__ + "." + QueryOptimizer.__qualname__ + "." + QueryOptimizer.compile.__name__
    with patch(path, return_value=OptimizationResults(**kwargs)):
        yield


def create_png(name: str = "image.png") -> File:
    bytes_io = BytesIO(PNG)
    bytes_io.seek(0)
    return File(bytes_io, name=name)
