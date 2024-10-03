from contextlib import contextmanager
from unittest.mock import Mock, patch

from django.core.management import call_command

from undine.management.commands import fetch_undine_static

COMMAND_NAME = fetch_undine_static.__name__.split(".")[-1]


@contextmanager
def patch_request():
    assert hasattr(fetch_undine_static, "requests"), "Mock is missing target for 'requests'!"
    path = "undine.management.commands.fetch_undine_static.requests.Session.get"
    with patch(path, return_value=Mock()) as mock_get:
        yield mock_get


@contextmanager
def patch_write_to_file():
    assert hasattr(fetch_undine_static, "Path"), "Mock is missing target for 'Path'!"
    path = "undine.management.commands.fetch_undine_static.Path.write_text"
    with patch(path, return_value=Mock()) as mock_get:
        yield mock_get


def test_fetch_undine_static():
    with patch_request() as mock_get, patch_write_to_file() as mock_write:
        call_command(COMMAND_NAME)

    assert mock_get.call_count == 6
    assert mock_write.call_count == 6

    assert mock_get.call_args_list[0][0][0] == "https://unpkg.com/graphiql@3.2.3/graphiql.min.js"
    assert mock_get.call_args_list[1][0][0] == "https://unpkg.com/graphiql@3.2.3/graphiql.min.css"
    assert mock_get.call_args_list[2][0][0] == "https://unpkg.com/react@18.3.1/umd/react.development.js"
    assert mock_get.call_args_list[3][0][0] == "https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js"
    assert mock_get.call_args_list[4][0][0] == "https://unpkg.com/@graphiql/plugin-explorer@3.0.2/dist/index.umd.js"
    assert mock_get.call_args_list[5][0][0] == "https://unpkg.com/@graphiql/plugin-explorer@3.0.2/dist/style.css"


def test_fetch_undine_static__arguments():
    with patch_request() as mock_get, patch_write_to_file() as mock_write:
        call_command(COMMAND_NAME, graphiql_version="1", react_version="2", plugin_explorer_version="3")

    assert mock_get.call_count == 6
    assert mock_write.call_count == 6

    assert mock_get.call_args_list[0][0][0] == "https://unpkg.com/graphiql@1/graphiql.min.js"
    assert mock_get.call_args_list[1][0][0] == "https://unpkg.com/graphiql@1/graphiql.min.css"
    assert mock_get.call_args_list[2][0][0] == "https://unpkg.com/react@2/umd/react.development.js"
    assert mock_get.call_args_list[3][0][0] == "https://unpkg.com/react-dom@2/umd/react-dom.development.js"
    assert mock_get.call_args_list[4][0][0] == "https://unpkg.com/@graphiql/plugin-explorer@3/dist/index.umd.js"
    assert mock_get.call_args_list[5][0][0] == "https://unpkg.com/@graphiql/plugin-explorer@3/dist/style.css"
