from collections.abc import Generator

from graphql import ExecutionResult, GraphQLError

from undine.hooks import LifecycleHook


class ErrorEnrichmentHook(LifecycleHook):
    """Catch errors and enrich them with status codes and error codes."""

    def run(self) -> Generator[None, None, None]:
        try:
            yield

        # Catch all exceptions raised in the hooking point and turn them into ExecutionResults.
        except Exception as err:
            msg = str(err)
            extensions = {"status_code": 500, "error_code": "INTERNAL_SERVER_ERROR"}
            new_error = GraphQLError(msg, extensions=extensions)
            self.context.result = ExecutionResult(errors=[new_error])
            return

        if self.context.result is None or self.context.result.errors is None:
            return

        # Enrich errors with status codes and error codes.
        for error in self.context.result.errors:
            if error.extensions is None:
                error.extensions = {}

            error.extensions.setdefault("status_code", 400)
            error.extensions.setdefault("error_code", "INTERNAL_SERVER_ERROR")
