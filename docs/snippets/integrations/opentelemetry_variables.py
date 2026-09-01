from typing import Any

from undine.hooks import LifecycleHookContext

SAFE_VARIABLES = {"first", "last", "offset"}


def traced_variables(context: LifecycleHookContext) -> dict[str, Any]:
    return {key: value for key, value in context.variables.items() if key in SAFE_VARIABLES}
