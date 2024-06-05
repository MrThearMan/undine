from __future__ import annotations

from http import HTTPStatus
from http.client import HTTPException

import pytest
from django.core.management import call_command

from tests.helpers import exact

from .helpers import COMMAND_NAME, MockResponse, patch_requests


def test_fetch_graphiql_static_for_undine() -> None:
    responses = {
        "/graphiql@3.8.3/graphiql.min.js": MockResponse(content="graphiql js"),
        "/graphiql@3.8.3/graphiql.min.css": MockResponse(content="graphiql css"),
        "/react@18.3.1/umd/react.development.js": MockResponse(content="react"),
        "/react-dom@18.3.1/umd/react-dom.development.js": MockResponse(content="react-dom"),
        "/@graphiql/plugin-explorer@3.2.5/dist/index.umd.js": MockResponse(content="explorer js"),
        "/@graphiql/plugin-explorer@3.2.5/dist/style.css": MockResponse(content="explorer css"),
    }

    with patch_requests(responses) as mock:
        call_command(COMMAND_NAME)

    assert mock.call_count == 6

    assert mock.mock_calls[0].kwargs["data"] == "graphiql js"
    assert mock.mock_calls[1].kwargs["data"] == "graphiql css"
    assert mock.mock_calls[2].kwargs["data"] == "react"
    assert mock.mock_calls[3].kwargs["data"] == "react-dom"
    assert mock.mock_calls[4].kwargs["data"] == "explorer js"
    assert mock.mock_calls[5].kwargs["data"] == "explorer css"


def test_fetch_graphiql_static_for_undine__arguments() -> None:
    responses = {
        "/graphiql@1/graphiql.min.js": MockResponse(content="graphiql js"),
        "/graphiql@1/graphiql.min.css": MockResponse(content="graphiql css"),
        "/react@2/umd/react.development.js": MockResponse(content="react"),
        "/react-dom@2/umd/react-dom.development.js": MockResponse(content="react-dom"),
        "/@graphiql/plugin-explorer@3/dist/index.umd.js": MockResponse(content="explorer js"),
        "/@graphiql/plugin-explorer@3/dist/style.css": MockResponse(content="explorer css"),
    }

    with patch_requests(responses) as mock:
        call_command(COMMAND_NAME, graphiql_version="1", react_version="2", plugin_explorer_version="3")

    assert mock.call_count == 6

    assert mock.mock_calls[0].kwargs["data"] == "graphiql js"
    assert mock.mock_calls[1].kwargs["data"] == "graphiql css"
    assert mock.mock_calls[2].kwargs["data"] == "react"
    assert mock.mock_calls[3].kwargs["data"] == "react-dom"
    assert mock.mock_calls[4].kwargs["data"] == "explorer js"
    assert mock.mock_calls[5].kwargs["data"] == "explorer css"


def test_fetch_graphiql_static_for_undine__errors() -> None:
    responses = {
        "/graphiql@3.8.3/graphiql.min.js": MockResponse(content="Missing", status=HTTPStatus.NOT_FOUND),
    }

    msg = "[404] Failed to fetch 'unpkg.com/graphiql@3.8.3/graphiql.min.js': Missing"

    with patch_requests(responses), pytest.raises(HTTPException, match=exact(msg)):
        call_command(COMMAND_NAME)
