import json
from collections.abc import Generator

from django.core.cache import cache
from graphql import ExecutionResult

from undine.hooks import LifecycleHook


class CachingHook(LifecycleHook):
    """Cache execution results."""

    TIMEOUT = 60

    def run(self) -> Generator[None, None, None]:
        cache_key = f"{self.context.source}:{json.dumps(self.context.variables)}:{self.context.request.user.pk}"
        was_cached = False

        # Check if the result is already cached.
        if cache_key in cache:
            data = cache.get(cache_key)
            was_cached = True

            # Setting results early will cause the hooking point to not run
            # and the graphql execution to exit early with this result.
            self.context.result = ExecutionResult(data=data)

        yield

        # If results where cached, the hooking point will not run, but the
        # hook's "after" portion will. Therefore, don't re-cache the result
        # if it was already cached.
        if was_cached:
            return

        if self.context.result is not None and self.context.result.data is not None:
            cache.set(cache_key, self.context.result.data, timeout=self.TIMEOUT)
