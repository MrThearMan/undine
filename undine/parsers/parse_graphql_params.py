from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.http.request import MediaType

from undine.dataclasses import GraphQLHttpParams
from undine.exceptions import (
    GraphQLMissingContentTypeError,
    GraphQLMissingDocumentIDError,
    GraphQLMissingFileMapError,
    GraphQLMissingOperationsError,
    GraphQLMissingQueryAndDocumentIDError,
    GraphQLMissingQueryError,
    GraphQLPersistedDocumentNotFoundError,
    GraphQLPersistedDocumentsNotSupportedError,
    GraphQLRequestDecodingError,
    GraphQLUnsupportedContentTypeError,
)
from undine.http.files import place_files
from undine.http.utils import decode_body, load_json_dict, parse_json_body
from undine.settings import undine_settings

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile

    from undine.typing import DjangoRequestProtocol

__all__ = [
    "GraphQLRequestParamsParser",
]


class GraphQLRequestParamsParser:
    """Parse GraphQLParams from a given HttpRequest."""

    @classmethod
    def run(cls, request: DjangoRequestProtocol) -> GraphQLHttpParams:
        data = cls.parse_body(request)
        return cls.get_graphql_params(data)

    @classmethod
    def parse_body(cls, request: DjangoRequestProtocol) -> dict[str, str]:
        if request.method == "GET":
            return request.GET.dict()  # type: ignore[return-value]

        if not request.content_type:
            raise GraphQLMissingContentTypeError

        content_type = MediaType(request.content_type)
        charset = str(content_type.params.get("charset", "utf-8"))

        if content_type.main_type == "application":
            if content_type.sub_type == "json":
                return parse_json_body(request.body, charset=charset)
            if content_type.sub_type == "graphql":
                return {"query": decode_body(request.body, charset=charset)}
            if content_type.sub_type == "x-www-form-urlencoded":
                return request.POST.dict()  # type: ignore[return-value]

        if (
            undine_settings.FILE_UPLOAD_ENABLED
            and content_type.main_type == "multipart"
            and content_type.sub_type == "form-data"
        ):
            if request.FILES:
                return cls.parse_file_uploads(request.POST.dict(), request.FILES.dict())  # type: ignore[arg-type]
            return request.POST.dict()  # type: ignore[return-value]

        raise GraphQLUnsupportedContentTypeError(content_type=content_type)

    @classmethod
    def parse_file_uploads(cls, post_data: dict[str, str], files: dict[str, UploadedFile]) -> dict[str, Any]:
        operations = cls.get_operations(post_data)
        files_map = cls.get_map(post_data)
        place_files(operations, files_map, files)
        return operations

    @classmethod
    def get_operations(cls, post_data: dict[str, str]) -> dict[str, Any]:
        operations: str | None = post_data.get("operations")
        if not isinstance(operations, str):
            raise GraphQLMissingOperationsError

        return load_json_dict(
            operations,
            decode_error_msg="The `operations` value must be a JSON object.",
            type_error_msg="The `operations` value is not a mapping.",
        )

    @classmethod
    def get_map(cls, post_data: dict[str, str]) -> dict[str, list[str]]:
        files_map_str: str | None = post_data.get("map")
        if not isinstance(files_map_str, str):
            raise GraphQLMissingFileMapError

        files_map = load_json_dict(
            files_map_str,
            decode_error_msg="The `map` value must be a JSON object.",
            type_error_msg="The `map` value is not a mapping.",
        )

        for value in files_map.values():
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                msg = "The `map` value is not a mapping from string to list of strings."
                raise GraphQLRequestDecodingError(msg)

        return files_map

    @classmethod
    def get_graphql_params(cls, data: dict[str, str]) -> GraphQLHttpParams:
        document = cls.parse_document(data)

        operation_name: str | None = data.get("operationName") or None

        variables: dict[str, str] | str | None = data.get("variables")
        if isinstance(variables, str):
            variables = load_json_dict(
                variables,
                decode_error_msg="Variables are invalid JSON.",
                type_error_msg="Variables must be a mapping.",
            )

        extensions: dict[str, str] | str | None = data.get("extensions")
        if isinstance(extensions, str):
            extensions = load_json_dict(
                extensions,
                decode_error_msg="Extensions are invalid JSON.",
                type_error_msg="Extensions must be a mapping.",
            )

        return GraphQLHttpParams(
            document=document,
            variables=variables or {},
            operation_name=operation_name,
            extensions=extensions or {},
        )

    @classmethod
    def parse_document(cls, data: dict[str, str]) -> str:
        persisted_documents_installed = "undine.persisted_documents" in settings.INSTALLED_APPS

        if not undine_settings.PERSISTED_DOCUMENTS_ONLY:
            query = data.get("query")
            if query:
                return query

            if not persisted_documents_installed:
                raise GraphQLMissingQueryError

        if not persisted_documents_installed:
            raise GraphQLPersistedDocumentsNotSupportedError

        document_id = data.get("documentId")
        if not document_id:
            if undine_settings.PERSISTED_DOCUMENTS_ONLY:
                raise GraphQLMissingDocumentIDError
            raise GraphQLMissingQueryAndDocumentIDError

        return cls.get_persisted_document(document_id)

    @classmethod
    def get_persisted_document(cls, document_id: str) -> str:
        from undine.persisted_documents.models import PersistedDocument  # noqa: PLC0415

        try:
            persisted_document = PersistedDocument.objects.get(document_id=document_id)
        except PersistedDocument.DoesNotExist as error:
            raise GraphQLPersistedDocumentNotFoundError(document_id=document_id) from error

        return persisted_document.document
