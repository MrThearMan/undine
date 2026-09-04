from typing import Any

from undine.hooks import LifecycleHookContext


def extra_context(context: LifecycleHookContext) -> dict[str, Any]:
    return {"lang": context.request.headers.get("Accept-Language", "en")}
