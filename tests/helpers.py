from __future__ import annotations

import json
import re
from contextlib import contextmanager
from io import BytesIO
from typing import TYPE_CHECKING, Any, MutableMapping, NamedTuple, TypedDict, TypeVar

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpHeaders, HttpRequest, QueryDict
from django.test.client import BOUNDARY
from django.utils.datastructures import MultiValueDict
from graphql import OperationType
from urllib3 import encode_multipart_formdata
from urllib3.fields import RequestField

from undine.errors.exceptions import UndineError
from undine.settings import SETTING_NAME, undine_settings

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http.request import MediaType

    from undine.typing import HttpMethod

__all__ = [
    "MockGQLInfo",
    "MockRequest",
    "exact",
    "get_graphql_multipart_spec_request",
    "has",
    "like",
    "override_undine_settings",
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


class like:  # noqa: N801
    """Compares a string to a regular expression pattern."""

    def __init__(self, query: str) -> None:
        self.pattern: re.Pattern[str] = re.compile(query)

    def __eq__(self, other: str) -> bool:
        if not isinstance(other, str):
            return False
        return self.pattern.match(other) is not None


class has:  # noqa: N801
    """
    Does the compared string contain the specified regular expression patterns?
    Use `str` of `like` objects for "contains" checks, and `bytes` for "excludes" checks.
    """

    def __init__(self, *patterns: str | bytes | like) -> None:
        self.patterns = patterns

    def __eq__(self, other: str) -> bool:
        if not isinstance(other, str):
            return False
        return all(
            pattern.decode() not in other if isinstance(pattern, bytes) else pattern in other
            for pattern in self.patterns
        )


def exact(msg: str) -> str:
    """Use in `with pytest.raises(..., match=<here>)` to match the 'msg' string exactly."""
    return f"^{re.escape(msg)}$"


@contextmanager
def override_undine_settings(**kwargs: Any) -> None:
    """Override the undine settings from the given kwargs."""
    old_settings = getattr(settings, SETTING_NAME)
    try:
        setattr(settings, SETTING_NAME, old_settings | kwargs)
        undine_settings.reload()
        yield
    finally:
        setattr(settings, SETTING_NAME, old_settings)
        undine_settings.reload()


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


class MockRequest:
    def __init__(  # noqa: PLR0913
        self,
        *,
        path: str = "/",
        method: HttpMethod = "GET",
        body: bytes | None = None,
        encoding: str = "utf-8",
        user: User | AnonymousUser | None = None,
        session: MutableMapping[str, Any] | None = None,
        accepted_types: list[MediaType] | None = None,
        headers: HttpHeaders | None = None,
        scheme: str = "http",
        content_type: str = "application/json",
    ) -> None:
        self.path = path
        self.method = method
        self.body = body or b""
        self.encoding = encoding
        self.user = user or AnonymousUser()
        self.session = session or {}
        self.accepted_types = accepted_types or []
        self.headers = headers or {}
        self.scheme = scheme
        self.content_type = content_type

        self.GET = QueryDict(mutable=True)
        self.POST = QueryDict(mutable=True)
        self.COOKIES = {}
        self.META = {}
        self.FILES = MultiValueDict()


class MockGQLInfo:
    def __init__(
        self,
        *,
        context: MockRequest | None = None,
        operation: OperationType = OperationType.QUERY,
    ) -> None:
        self._context = context or MockRequest()
        self.operation = operation

    @property
    def context(self) -> MockRequest:
        return self._context
