# Error masking

## Context

Undine returns the raw text of unexpected exceptions to the client.

**Verified by experiment on this machine.** A field resolver raising
`RuntimeError("DB password is hunter2 at db.internal:5432")` produces, with default settings:

```
message:    'DB password is hunter2 at db.internal:5432'
extensions: {'status_code': 500}
```

Strawberry ships `MaskErrors(should_mask_error, error_message)` for this; Undine has no
equivalent. Note this is *not* gated on `DEBUG` — the message above is what a production client
sees today.

### Undine can do better than Strawberry's default, and should

`strawberry/extensions/mask_errors.py`'s `default_should_mask_error` returns `True` for
**every** error, so by default it masks validation errors, permission errors and everything else
into `"Unexpected error."`. That is a blunt default that discards genuinely useful client-facing
messages, and users must write a `should_mask_error` predicate to get sane behaviour back.

Undine already classifies errors precisely, in `graphql_errors_hook`
(`undine/utils/graphql/utils.py:346-367`):

```python
if error.original_error is None or isinstance(error.original_error, GraphQLError):
    extensions.setdefault("status_code", HTTPStatus.BAD_REQUEST)
else:
    extensions.setdefault("status_code", HTTPStatus.INTERNAL_SERVER_ERROR)
```

That distinction — "deliberately raised GraphQL error" versus "something blew up" — is exactly
the line masking should follow. The default should be **mask 5xx, pass through 4xx**, which
preserves every deliberate message (`GraphQLPermissionError`, `GraphQLValidationError`, field
validation output, errors-as-data) while hiding the ones that leak internals. A predicate setting
lets users override, as Strawberry does.

### There is one obvious place to put this

`graphql_errors_hook` is the single chokepoint: `get_error_execution_result` routes list,
`GraphQLErrorGroup` and single-error cases through it (`undine/utils/graphql/utils.py:183-193`),
`undine/execution.py` calls it on the success-with-errors paths (lines ~732 and ~737), and the
websocket path calls it too (`undine/utils/graphql/websocket.py:436`). It already iterates every
error and already sets the status code that the masking decision depends on.

This means masking need not be a `LifecycleHook` at all, unlike the other items in this series.
Consider carefully which is right:

- **In `graphql_errors_hook`**: covers every transport by construction, including websockets and
  the incremental/streaming paths. Cannot be forgotten.
- **As a `LifecycleHook`**: consistent with `RequestCacheHook` etc. and opt-in per project, but
  operates on `context.result` and would need to handle `ExecutionResult`,
  `ExperimentalIncrementalExecutionResults` (`GraphQLResult` is a union of the two,
  `undine/typing.py:336`) and the streaming cases separately. Strawberry needs a separate
  `on_stream_result` hook for exactly this reason.

The chokepoint is the safer design; a security-relevant filter that a transport can bypass is
worse than one that is always on. **Recommendation: implement in `graphql_errors_hook`, controlled
by settings.** Raise with the user if the opt-in-hook shape is preferred anyway.

## The work

### 1. Settings

Follow the existing settings conventions (`.agents/docs/library-settings.md`):

- A predicate deciding whether a given error is masked, defaulting to "mask iff status is 5xx".
  Follow the callback-setting convention (`REQUEST_CACHE_READ_PREDICATE`,
  `PERSISTED_DOCUMENTS_PERMISSION_CALLBACK`).
- The replacement message, defaulting to something like `"Unexpected error."`.

**Decided by the user: masking defaults to ON**, on the same reasoning as introspection being
disabled by default — security first. The current behaviour leaks internals in production with no
warning, so the safe default is worth the behaviour change. This warrants a release note, since
existing users will see previously visible messages disappear from responses (they remain in the
logs — see step 3).

### 2. What to strip

Replacing `message` is not sufficient on its own. Also consider:

- `extensions` — may carry `error_code` and anything a resolver attached. Decide what survives;
  `status_code` should, since clients and the HTTP layer depend on it.
- `original_error` — Strawberry sets it to `None` when anonymising. Do the same so nothing
  downstream can re-derive the original message.
- `path` / `locations` — Strawberry preserves these, and they are useful for clients without
  leaking internals. Preserve.

**`INCLUDE_ERROR_TRACEBACK` — decided by the user.** It is primarily a debug setting, but it must
not defeat masking: when an error is masked, its traceback must **not** be sent to the client,
regardless of `INCLUDE_ERROR_TRACEBACK`. The traceback must still be **logged** (step 3). So
masking wins over the traceback setting for the client-facing payload only.

Practically: `graphql_errors_hook` currently does `extensions["traceback"] = get_traceback(...)`
under `if undine_settings.INCLUDE_ERROR_TRACEBACK` (`undine/utils/graphql/utils.py:362-363`).
That branch must additionally be conditional on the error not being masked. Document this
interaction explicitly in the settings docs for both settings — a user who turns on
`INCLUDE_ERROR_TRACEBACK` and sees no traceback needs to find out why without reading the source.

### 3. Logging must survive masking

`graphql_errors_hook` currently calls `log_traceback(error.__traceback__)`
(`undine/utils/graphql/utils.py:359-360`). Masking must not stop the server-side log — the whole
point is that the operator still sees the error while the client does not. Make sure the log
happens before, or independently of, the masking step.

### 4. Errors-as-data should be unaffected — confirm it

Undine's errors-as-data feature requires **explicit opt-in**: an `Entrypoint` only returns typed
errors as values when the user lists exception types in its `errors` argument
(`undine/entrypoint.py:172-173, 188`). `error_union_resolver_wrapper` then matches raised
exceptions against exactly that list and **re-raises anything not listed**
(`undine/utils/graphql/error_unions.py:76-94`). An unexpected 500 therefore cannot reach the
errors-as-data path by accident — it propagates as a normal error and gets masked like any other.

The user's assessment is that this is therefore a non-issue. It costs little to confirm, so add a
test rather than reasoning about it: an entrypoint declaring `errors=[SomeError]` should still
return `SomeError` as data with its real message under masking, while an unlisted `RuntimeError`
raised from the same entrypoint is masked in the `errors` array.

## Done when

- With masking enabled, a resolver raising `RuntimeError("secret")` yields the configured generic
  message; the string `"secret"` appears nowhere in the response, including in `extensions`.
- The same error is still logged server-side with its traceback.
- Masking is on by default: a project that sets no masking settings at all does not leak the
  raw exception message.
- With `INCLUDE_ERROR_TRACEBACK = True` **and** masking active, the traceback is absent from the
  client response but still present in the logs.
- `GraphQLPermissionError` and `GraphQLValidationError` messages reach the client unchanged under
  the default predicate — masking 5xx must not swallow deliberate 4xx messages.
- An `Entrypoint` with `errors=[SomeError]` still returns `SomeError` as data with its real
  message, while an unlisted exception from the same entrypoint is masked in the `errors` array.
- Masking applies over HTTP, websockets, SSE and the incremental/streaming paths. If implemented
  in `graphql_errors_hook` this follows by construction, but test at least the websocket path
  (`undine/utils/graphql/websocket.py:436`) since it is a separate call site.
- A custom predicate can mask a specific 4xx error, and can let a specific 5xx through.
- `docs/settings.md` documents the masking settings and their interaction with
  `INCLUDE_ERROR_TRACEBACK`, from both directions.
