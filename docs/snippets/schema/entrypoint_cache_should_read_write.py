from undine.hooks import LifecycleHookContext


def should_read_from_cache(context: LifecycleHookContext) -> bool:
    return context.request.headers.get("X-Cache-Read", "false").lower() == "true"


def should_write_to_cache(context: LifecycleHookContext) -> bool:
    return context.request.headers.get("X-Cache-Write", "false").lower() == "true"
