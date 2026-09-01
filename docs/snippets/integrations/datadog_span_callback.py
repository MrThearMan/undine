from ddtrace.trace import Span

from undine.hooks import LifecycleHookContext


def tag_with_error_count(span: Span, context: LifecycleHookContext) -> None:
    error_count = len(context.result.errors or []) if context.result is not None else 0  # type: ignore[union-attr]
    span.set_tag("graphql.error_count", error_count)
