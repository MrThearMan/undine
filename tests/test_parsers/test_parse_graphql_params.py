import re

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpRequest

from tests.helpers import get_graphql_multipart_spec_request
from undine.errors import GraphQLStatusError
from undine.parsers import GraphQLRequestParamsParser
from undine.typing import GraphQLParams


def test_parse_graphql_params__get_request():
    request = HttpRequest()
    request.method = "GET"
    request.GET.appendlist("query", "query MyQuery { hello }")
    request.GET.appendlist("variables", "{}")
    request.GET.appendlist("operationName", "MyQuery")
    request.GET.appendlist("extensions", "{}")
    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLParams)
    assert params.query == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name == "MyQuery"
    assert params.extensions == {}


def test_parse_graphql_params__no_content_type_header():
    request = HttpRequest()
    request.method = "POST"
    request.POST.appendlist("query", "query MyQuery { hello }")
    request.POST.appendlist("variables", "{}")

    msg = "Must provide a 'Content-Type' header."
    with pytest.raises(GraphQLStatusError, match=re.escape(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__json_content():
    request = HttpRequest()
    request.method = "POST"
    request.content_type = "application/json"
    request._body = b'{"query": "query MyQuery { hello }", "variables": {}}'

    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLParams)
    assert params.query == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name is None
    assert params.extensions is None


def test_parse_graphql_params__json_content__decode_error():
    request = HttpRequest()
    request.method = "POST"
    request.content_type = "application/json"
    request._body = b"\xd3\x01Z\x05\xce\x18i\xaa\xadA\xfe)\\\xcc\xf7C"

    msg = "Could not decode body with encoding 'utf-8'."
    with pytest.raises(GraphQLStatusError, match=re.escape(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__json_content__not_json():
    request = HttpRequest()
    request.method = "POST"
    request.content_type = "application/json"
    request._body = b'{"query": query MyQuery { hello }'

    msg = "Could not load JSON body."
    with pytest.raises(GraphQLStatusError, match=re.escape(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__json_content__not_dict():
    request = HttpRequest()
    request.method = "POST"
    request.content_type = "application/json"
    request._body = b'[{"query": "query MyQuery { hello }"}]'

    msg = "JSON body should convert to a dictionary."
    with pytest.raises(GraphQLStatusError, match=re.escape(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__graphql_content():
    request = HttpRequest()
    request.method = "POST"
    request.content_type = "application/graphql"
    request._body = b"query MyQuery { hello }"

    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLParams)
    assert params.query == "query MyQuery { hello }"
    assert params.variables is None
    assert params.operation_name is None
    assert params.extensions is None


def test_parse_graphql_params__form_urlencoded_content():
    request = HttpRequest()
    request.method = "POST"
    request.content_type = "application/x-www-form-urlencoded"
    request.POST.appendlist("query", "query MyQuery { hello }")
    request.POST.appendlist("variables", "{}")

    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLParams)
    assert params.query == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name is None
    assert params.extensions is None


def test_parse_graphql_params__multipart_content():
    request = HttpRequest()
    request.method = "POST"
    request.content_type = "multipart/form-data"
    request.POST.appendlist("query", "query MyQuery { hello }")
    request.POST.appendlist("variables", "{}")

    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLParams)
    assert params.query == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name is None
    assert params.extensions is None


def test_parse_graphql_params__multipart_content__file_upload():
    request = get_graphql_multipart_spec_request()
    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLParams)
    assert params.query == "mutation($file: File!) { files(files: $file) { id } }"
    assert list(params.variables.keys()) == ["file"]
    assert isinstance(params.variables["file"], InMemoryUploadedFile)
    assert params.operation_name is None
    assert params.extensions is None


def test_parse_graphql_params__multipart_content__file_upload__missing_operations():
    request = get_graphql_multipart_spec_request(op=None)

    msg = "File upload must contain an `operations` value."
    with pytest.raises(GraphQLStatusError, match=re.escape(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__multipart_content__file_upload__operations_not_a_mapping():
    request = get_graphql_multipart_spec_request(op="hello world")

    msg = "The `operations` value is not a mapping."
    with pytest.raises(GraphQLStatusError, match=re.escape(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__multipart_content__file_upload__missing_map():
    request = get_graphql_multipart_spec_request(op_map=None)

    msg = "File upload must contain an `map` value."
    with pytest.raises(GraphQLStatusError, match=re.escape(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__multipart_content__file_upload__map_not_a_mapping():
    request = get_graphql_multipart_spec_request(op_map="hello world")

    msg = "The `map` value is not a mapping."
    with pytest.raises(GraphQLStatusError, match=re.escape(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__multipart_content__file_upload__values_must_be_a_list():
    request = get_graphql_multipart_spec_request(op_map={"0": "variables.file"})

    msg = "The `map` value is not a mapping from string to list of strings."
    with pytest.raises(GraphQLStatusError, match=re.escape(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__unsupported_content():
    request = HttpRequest()
    request.method = "POST"
    request.content_type = "text/plain"

    msg = "'text/plain' is not a supported content type."
    with pytest.raises(GraphQLStatusError, match=re.escape(msg)):
        GraphQLRequestParamsParser.run(request)
