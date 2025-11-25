from django.http import HttpRequest

from undine.exceptions import GraphQLPermissionError


def persisted_documents_permissions(request: HttpRequest, document_map: dict[str, str]) -> None:
    if not request.user.is_superuser:
        msg = "You do not have permission to register persisted documents."
        raise GraphQLPermissionError(msg)
