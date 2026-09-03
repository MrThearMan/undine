from http import HTTPStatus

from graphql import GraphQLError

IGNORED_ERROR_CODES = {"PERMISSION_DENIED", "VALIDATION_ERROR"}


def should_report_error(error: GraphQLError) -> bool:
    if error.extensions.get("error_code") in IGNORED_ERROR_CODES:
        return False
    return error.extensions.get("status_code") == HTTPStatus.INTERNAL_SERVER_ERROR
