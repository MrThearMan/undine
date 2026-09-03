from undine.hooks import LifecycleHookContext
from undine.integrations.sentry import RecordedSpan


def tag_with_error_count(span: RecordedSpan, context: LifecycleHookContext) -> None:
    error_count = len(context.result.errors or []) if context.result is not None else 0  # type: ignore[union-attr]
    span.set_data("graphql.error_count", error_count)
