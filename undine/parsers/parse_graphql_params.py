from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.http.request import MediaType

from undine.dataclasses import GraphQLHttpParams
from undine.exceptions import (
    GraphQLAPQHashInvalidError,
    GraphQLAPQHashMissingError,
    GraphQLAPQNotSuppoertedError,
    GraphQLAPQVersionInvalidError,
    GraphQLAPQVersionMissingError,
    GraphQLAPQVersionNotSupportedError,
    GraphQLMissingContentTypeError,
    GraphQLMissingDocumentError,
    GraphQLMissingDocumentIDError,
    GraphQLMissingFileMapError,
    GraphQLMissingOperationsError,
    GraphQLMissingQueryError,
    GraphQLPersistedDocumentNotFoundError,
    GraphQLPersistedDocumentsNotSupportedError,
    GraphQLRequestDecodingError,
    GraphQLUnsupportedContentTypeError,
)
from undine.http.files import place_files
from undine.http.utils import decode_body, load_json_dict, parse_json_body
from undine.settings import undine_settings
from undine.utils.reflection import is_list_of

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
    async def run_async(cls, request: DjangoRequestProtocol) -> GraphQLHttpParams:
        data = cls.parse_body(request)
        return await cls.get_graphql_params_async(data)

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
            if not is_list_of(value, str, allow_empty=True):
                msg = "The `map` value is not a mapping from string to list of strings."
                raise GraphQLRequestDecodingError(msg)

        return files_map

    @classmethod
    def get_graphql_params(cls, data: dict[str, Any]) -> GraphQLHttpParams:
        extensions = cls.get_operation_extensions(data)
        document = cls.parse_document(data, extensions)
        variables = cls.get_operation_variables(data)
        operation_name = cls.get_operation_name(data)

        return GraphQLHttpParams(
            document=document,
            variables=variables,
            operation_name=operation_name,
            extensions=extensions,
        )

    @classmethod
    async def get_graphql_params_async(cls, data: dict[str, Any]) -> GraphQLHttpParams:
        extensions = cls.get_operation_extensions(data)
        document = await cls.parse_document_async(data, extensions)
        variables = cls.get_operation_variables(data)
        operation_name = cls.get_operation_name(data)

        return GraphQLHttpParams(
            document=document,
            variables=variables,
            operation_name=operation_name,
            extensions=extensions,
        )

    @classmethod
    def get_operation_name(cls, data: dict[str, Any]) -> str | None:
        return data.get("operationName") or None

    @classmethod
    def get_operation_variables(cls, data: dict[str, Any]) -> dict[str, str]:
        variables: dict[str, str] | str | None = data.get("variables")
        if isinstance(variables, str):
            variables = load_json_dict(
                variables,
                decode_error_msg="Variables are invalid JSON.",
                type_error_msg="Variables must be a mapping.",
            )
        return variables or {}

    @classmethod
    def get_operation_extensions(cls, data: dict[str, Any]) -> dict[str, str]:
        extensions: dict[str, str] | str | None = data.get("extensions")
        if isinstance(extensions, str):
            extensions = load_json_dict(
                extensions,
                decode_error_msg="Extensions are invalid JSON.",
                type_error_msg="Extensions must be a mapping.",
            )
        return extensions or {}

    @classmethod
    def parse_document(cls, data: dict[str, Any], extensions: dict[str, str]) -> str:
        if not undine_settings.PERSISTED_DOCUMENTS_ONLY:
            query = data.get("query")
            if query:
                return query

            if not cls.persisted_documents_installed():
                raise GraphQLMissingQueryError

        if not cls.persisted_documents_installed():
            # Add 'code' so that Apollo Client knows what's going on.
            extensions = {"code": "PERSISTED_QUERY_NOT_SUPPORTED"}
            raise GraphQLPersistedDocumentsNotSupportedError(extensions=extensions)

        document_id = data.get("documentId")
        if not document_id:
            document_id = cls.get_apq_document_id(extensions)

        if not document_id:
            if undine_settings.PERSISTED_DOCUMENTS_ONLY:
                raise GraphQLMissingDocumentIDError
            raise GraphQLMissingDocumentError

        return cls.get_persisted_document(document_id)

    @classmethod
    async def parse_document_async(cls, data: dict[str, Any], extensions: dict[str, str]) -> str:
        if not undine_settings.PERSISTED_DOCUMENTS_ONLY:
            query = data.get("query")
            if query:
                return query

            if not cls.persisted_documents_installed():
                raise GraphQLMissingQueryError

        if not cls.persisted_documents_installed():
            # Add 'code' so that Apollo Client knows what's going on.
            extensions = {"code": "PERSISTED_QUERY_NOT_SUPPORTED"}
            raise GraphQLPersistedDocumentsNotSupportedError(extensions=extensions)

        document_id = data.get("documentId")
        if not document_id:
            document_id = cls.get_apq_document_id(extensions)

        if not document_id:
            if undine_settings.PERSISTED_DOCUMENTS_ONLY:
                raise GraphQLMissingDocumentIDError
            raise GraphQLMissingDocumentError

        return await cls.get_persisted_document_async(document_id)

    @classmethod
    def persisted_documents_installed(cls) -> bool:
        return "undine.persisted_documents" in settings.INSTALLED_APPS

    @classmethod
    def get_apq_document_id(cls, extensions: dict[str, Any]) -> str | None:
        persisted_query: dict[str, Any] | None = extensions.get("persistedQuery")
        if persisted_query is None:
            return None

        if not undine_settings.AUTOMATIC_PERSISTED_QUERIES_ENABLED:
            # Add 'code' so that Apollo Client knows what's going on.
            extensions = {"code": "PERSISTED_QUERY_NOT_SUPPORTED"}
            raise GraphQLAPQNotSuppoertedError(extensions=extensions)

        version: int | None = persisted_query.get("version")
        if version is None:
            raise GraphQLAPQVersionMissingError

        if not isinstance(version, int):
            raise GraphQLAPQVersionInvalidError

        if version != 1:
            raise GraphQLAPQVersionNotSupportedError(version=version)

        sha256_hash: str | None = persisted_query.get("sha256Hash")
        if sha256_hash is None:
            raise GraphQLAPQHashMissingError

        if not isinstance(sha256_hash, str):
            raise GraphQLAPQHashInvalidError

        # Mark the persisted query as used so that we won't try to save it again.
        extensions["persistedQueryUsed"] = True

        return f"sha256:{sha256_hash}"

    @classmethod
    def get_persisted_document(cls, document_id: str) -> str:
        from undine.persisted_documents.models import PersistedDocument  # noqa: PLC0415

        try:
            persisted_document = PersistedDocument.objects.get(document_id=document_id)
        except PersistedDocument.DoesNotExist as error:
            # Add 'code' so that Apollo Client knows what's going on.
            extensions = {"code": "PERSISTED_DOCUMENT_NOT_FOUND"}
            raise GraphQLPersistedDocumentNotFoundError(document_id=document_id, extensions=extensions) from error

        return persisted_document.document

    @classmethod
    async def get_persisted_document_async(cls, document_id: str) -> str:
        from undine.persisted_documents.models import PersistedDocument  # noqa: PLC0415

        try:
            persisted_document = await PersistedDocument.objects.aget(document_id=document_id)
        except PersistedDocument.DoesNotExist as error:
            # Add 'code' so that Apollo Client knows what's going on.
            extensions = {"code": "PERSISTED_DOCUMENT_NOT_FOUND"}
            raise GraphQLPersistedDocumentNotFoundError(document_id=document_id, extensions=extensions) from error

        return persisted_document.document
