# django-graphql-jwt findings

Version checked: 0.4.0 (2023-08-04, latest on PyPI). Previous release 0.3.4 was 2021-08-11. Last repo commit is 2023-08-04. The project looks unmaintained.
Package `django-graphql-jwt`. Import `graphql_jwt`. Classifier is "Development Status :: 4 - Beta".
It is an auth add-on for graphene-django only (`graphene>=2.1.5`, `graphene-django>=2.0.0`, `PyJWT>=2,<3`). It supports graphene 2 and 3. It does not work with Strawberry or Undine.
It has no schema, type, filter or mutation-generation features. Scope is JWT issue, verify, refresh, revoke, and resolver decorators.

## Setup

- Three pieces are required: `graphql_jwt.middleware.JSONWebTokenMiddleware` in `GRAPHENE["MIDDLEWARE"]`, `graphql_jwt.backends.JSONWebTokenBackend` in `AUTHENTICATION_BACKENDS`, and Django `AuthenticationMiddleware`.
- `JSONWebTokenBackend.authenticate(request, **kwargs)` reads the token and returns the user. It skips itself during `tokenAuth` (flag `request._jwt_token_auth`). `get_user(user_id)` added in 0.3.4.
- All settings live in one Django setting dict `GRAPHQL_JWT`. `graphql_jwt.settings.jwt_settings` reads it lazily, imports dotted-path handlers, and reloads on the `setting_changed` signal (test `override_settings` works).

## Token transport

- HTTP header: `Authorization: JWT <token>`. Header name `JWT_AUTH_HEADER_NAME` (default `"HTTP_AUTHORIZATION"`). Prefix `JWT_AUTH_HEADER_PREFIX` (default `"JWT"`, compare is case-insensitive). No built-in `Bearer` default.
- Cookie: wrap the view with `graphql_jwt.decorators.jwt_cookie(GraphQLView.as_view())`. It sets `request.jwt_cookie = True`. After `tokenAuth` or `refreshToken` it sets an `HttpOnly` cookie `JWT_COOKIE_NAME` (default `"JWT"`) and, for long running refresh tokens, `JWT_REFRESH_TOKEN_COOKIE_NAME` (default `"JWT-refresh-token"`).
- Cookie options: `JWT_COOKIE_SECURE`, `JWT_COOKIE_PATH`, `JWT_COOKIE_DOMAIN`, `JWT_COOKIE_SAMESITE`. `HttpOnly` is always on.
- The header wins. If the header is missing or malformed, the cookie is read (`graphql_jwt.utils.get_http_authorization`).
- Per-argument auth: `JWT_ALLOW_ARGUMENT=True` and `JWT_ARGUMENT_NAME` (default `"token"`). The user adds a `token` argument to a field. The middleware authenticates that field subtree with that token. One operation can use several credentials through aliases (`viewerA: viewer(token: $a)`). Also reads `input.token` for Relay input.
- Per-argument auth caches the user per path with `graphql_jwt.path.PathDict`. Child fields inherit the user of the nearest parent path.
- `JWT_HIDE_TOKEN_FIELDS=True`: remove `token` and `refreshToken` output fields from the mutations. Used with cookie auth to keep tokens out of JS (XSS).
- `JWT_CSRF_ROTATION=True`: call Django `rotate_token()` each time a token or refresh token is issued.
- Docs recommend `CsrfViewMiddleware` with cookie auth. The library does not enforce CSRF itself.
- No WebSocket or subscription auth. No `connection_init` payload handling. No SSE support.

## Mutations (`graphql_jwt` and `graphql_jwt.relay`)

- `ObtainJSONWebToken` (`tokenAuth`): arguments `<USERNAME_FIELD>` and `password`. The username argument name follows `get_user_model().USERNAME_FIELD`. Returns `token`, `payload` (GenericScalar), `refreshExpiresIn`, and `refreshToken` when long running refresh is on. Calls `django.contrib.auth.authenticate()`, so any auth backend works.
- `JSONWebTokenMutation`: abstract base for a custom obtain mutation. Subclass it and define `resolve(cls, root, info, **kwargs)` to add output fields (for example `user`). A `resolve` method is asserted at class creation.
- `Verify` (`verifyToken`): argument `token`. Returns `payload`. Falls back to the cookie when the argument is missing (`ensure_token`).
- `Refresh` (`refreshToken`): single-token mode takes `token`. Long running mode takes `refreshToken`. The class picks its mixin at import time from `JWT_LONG_RUNNING_REFRESH_TOKEN` (`KeepAliveRefreshMixin` or `RefreshTokenMixin`).
- `Revoke` (`revokeToken`): argument `refreshToken`. Returns `revoked` as a Unix timestamp. Only for long running refresh tokens.
- `DeleteJSONWebTokenCookie` (`deleteTokenCookie`), `DeleteRefreshTokenCookie` (`deleteRefreshTokenCookie`): server-side logout for `HttpOnly` cookies. Return `deleted`.
- `graphql_jwt.relay.*`: the same set as `graphene.ClientIDMutation` with a single `input` argument and `clientMutationId`.
- These mutations are in `JWT_ALLOW_ANY_CLASSES` by default, so the middleware does not try to authenticate them.
- No logout mutation for header-based tokens. No "revoke all tokens of a user" mutation.
- No register, password reset, email verification, or social login mutations. Those are in the separate `django-graphql-auth` package.

## Access token (JWT) handling (`graphql_jwt.utils`)

- Built on PyJWT. `JWT_ALGORITHM` (default `"HS256"`). `JWT_SECRET_KEY` (default `settings.SECRET_KEY`).
- Asymmetric keys: `JWT_PRIVATE_KEY` signs and `JWT_PUBLIC_KEY` verifies. They override `JWT_SECRET_KEY`. No JWKS endpoint or JWKS fetch. No key rotation or multiple keys (`kid`).
- Claims: `JWT_AUDIENCE` (`aud`), `JWT_ISSUER` (`iss`), `JWT_LEEWAY`, `JWT_VERIFY` (signature check), `JWT_VERIFY_EXPIRATION` (default `False`, so tokens do not expire unless enabled), `JWT_EXPIRATION_DELTA` (default 5 minutes).
- Default payload (`jwt_payload`): `{<USERNAME_FIELD>: username, "exp": ..., "origIat": ...}`. `origIat` only when `JWT_ALLOW_REFRESH=True`. No `jti`, `iat`, `sub` or user pk by default.
- Pluggable handlers (dotted path or callable): `JWT_ENCODE_HANDLER`, `JWT_DECODE_HANDLER`, `JWT_PAYLOAD_HANDLER`, `JWT_PAYLOAD_GET_USERNAME_HANDLER`, `JWT_GET_USER_BY_NATURAL_KEY_HANDLER`. All take a `context` argument.
- User lookup uses `get_by_natural_key(username)`. Inactive users (`is_active=False`) are rejected with "User is disabled".
- Access tokens are stateless. They cannot be revoked. No denylist.

## Refresh tokens

- Single token refresh (default): `refreshToken(token)` issues a new JWT while `origIat + JWT_REFRESH_EXPIRATION_DELTA` (default 7 days) is not reached. `JWT_ALLOW_REFRESH` turns refresh on or off. `JWT_REFRESH_EXPIRED_HANDLER(orig_iat, context)` decides expiry. Returning `False` gives unlimited refresh.
- Long running refresh tokens: `JWT_LONG_RUNNING_REFRESH_TOKEN=True` plus app `graphql_jwt.refresh_token.apps.RefreshTokenConfig`. Opaque random tokens are stored in the database.
- Model `graphql_jwt.refresh_token.models.RefreshToken`. Swappable with `JWT_REFRESH_TOKEN_MODEL` and `AbstractRefreshToken`. Fields `user`, `token`, `created`, `revoked`. Methods `is_expired()`, `revoke()`, `reuse()`, `get_token()`.
- Tokens are stored in plain text by default. `_cached_token` and `JWT_GET_REFRESH_TOKEN_HANDLER` let users hash them in a custom model. Hashing is not built in.
- `JWT_REFRESH_TOKEN_N_BYTES` (default 20): token length.
- Rotation: each refresh creates a new refresh token. The old one stays valid unless revoked. One-time use needs a user-written `refresh_token_rotated` receiver that calls `refresh_token.revoke(request)`. No automatic reuse detection.
- `JWT_REUSE_REFRESH_TOKENS=True`: overwrite the existing row with a new token instead of creating a new row.
- Tokens are created lazily with `refresh_token_lazy` (a Django `lazy` string). The row is only written when the field is resolved.
- `manage.py cleartokens [--expired]`: delete revoked tokens, and expired tokens with `--expired`.
- Django admin: `RefreshTokenAdmin` with `RevokedFilter`, `ExpiredFilter` and a bulk "Revoke" action. `RefreshTokenQuerySet.expired()` annotation.

## Authorization decorators (`graphql_jwt.decorators`)

- `@login_required`, `@staff_member_required`, `@superuser_required`: check `info.context.user`.
- `@permission_required("app.perm")` or an iterable of perms: uses `user.has_perms()`. All perms must pass.
- `@user_passes_test(test_func, exc=PermissionDenied)`: generic check. Custom exception class allowed.
- Decorators work on resolvers and on `Mutation.mutate` classmethods. They find `info` by scanning the args for `ResolveInfo`.
- Failure raises `graphql_jwt.exceptions.PermissionDenied` ("You do not have permission to perform this action"). It becomes a normal GraphQL error.
- `JWT_ALLOW_ANY_HANDLER` (default `graphql_jwt.middleware.allow_any`) and `JWT_ALLOW_ANY_CLASSES`: skip authentication for root fields whose Graphene type is a subclass of the listed classes. This decides whether to authenticate, not whether to authorize.
- No object-level permissions. No type-level or field-level permission classes. No schema hiding per user. No queryset filtering by user.
- Decorators are sync only. They do not await async resolvers. The middleware is a sync graphene middleware.

## Errors (`graphql_jwt.exceptions`)

- `JSONWebTokenError` (base), `PermissionDenied`, `JSONWebTokenExpired` ("Signature has expired").
- Messages: "Please enter valid credentials", "Error decoding signature", "Invalid token", "Invalid payload", "User is disabled", "Refresh has expired", "Refresh token is expired", "Invalid refresh token", "Token is required", "Refresh token is required".
- No error codes in `extensions`. Clients must match on message text.
- Messages are translated with Django gettext. Locales: ar, de, es, fr, nl, pt_BR, zh_Hans.

## Signals

- `graphql_jwt.signals.token_issued(sender, request, user)`: on successful `tokenAuth`.
- `graphql_jwt.signals.token_refreshed(sender, request, user)`: on single-token refresh.
- `graphql_jwt.refresh_token.signals.refresh_token_rotated(sender, request, refresh_token, refresh_token_issued)`.
- `graphql_jwt.refresh_token.signals.refresh_token_revoked(sender, request, refresh_token)`.
- No own signal on failed login. Django `user_login_failed` still fires because `tokenAuth` calls `authenticate()`.

## Shortcuts (`graphql_jwt.shortcuts`)

- `get_token(user, context=None, **extra)`: make a JWT for a user. Extra kwargs are merged into the payload.
- `get_user_by_token(token, context=None)`.
- `create_refresh_token(user, refresh_token=None)`, `get_refresh_token(token, context=None)`.

## Testing (`graphql_jwt.testcases`)

- `JSONWebTokenTestCase`: Django `TestCase` with `client_class = JSONWebTokenClient`.
- `JSONWebTokenClient.authenticate(user)`: set the auth header with a fresh token. `logout()`, `credentials(**headers)`.
- `client.execute(query, variables)`: runs the schema directly (no HTTP view) with `JSONWebTokenMiddleware`. Returns a graphql `ExecutionResult`.
- `SchemaRequestFactory.schema(**kwargs)` to use a different schema. `.middleware([...])` to change middleware.
- No pytest fixtures. No cookie-based test helper.

## Not supported or not in scope

- No Strawberry or Undine support. Graphene only.
- No async views, async middleware or async decorators.
- No WebSocket, subscription or SSE authentication.
- No access token revocation, denylist or `jti` tracking.
- No refresh token reuse detection or token family invalidation.
- No refresh token hashing built in.
- No JWKS, OIDC, OAuth2 or external identity provider support.
- No session-auth mutations (login/logout with Django sessions).
- No user registration, password change or reset, email verification or 2FA.
- No rate limiting or brute-force protection on `tokenAuth`.
- No error codes, only message strings.
- No type hints, no `py.typed`.
- Docs have no page on the per-path user cache (`PathDict`), `JWT_ALLOW_ANY_CLASSES` defaults, the admin integration or `get_token(**extra)`.

## Sources

Repo: https://github.com/flavors/django-graphql-jwt (shallow clone at `/tmp/django-graphql-jwt`, last commit 2023-08-04).

Docs read (repo `docs/` source of https://django-graphql-jwt.domake.io/):
- `docs/index.rst`, `quickstart.rst`, `authentication.rst`, `decorators.rst`, `refresh_token.rst`
- `docs/customizing.rst`, `relay.rst`, `signals.rst`, `tests.rst`, `settings.rst`

Changelog: `CHANGELOG.rst` in the repo (0.0.1 to 0.4.0). Also https://django-graphql-jwt.domake.io/changelog.

Source files checked:
- `graphql_jwt/__init__.py`, `settings.py`, `middleware.py`, `backends.py`, `decorators.py`, `mixins.py`, `mutations.py`, `relay.py`
- `graphql_jwt/utils.py`, `shortcuts.py`, `exceptions.py`, `signals.py`, `path.py`, `_compat.py`, `testcases.py`
- `graphql_jwt/refresh_token/models.py`, `managers.py`, `mixins.py`, `mutations.py`, `relay.py`, `shortcuts.py`, `signals.py`, `utils.py`, `decorators.py`, `admin/__init__.py`, `admin/filters.py`, `management/commands/cleartokens.py`
- `pyproject.toml`

`/llms.txt` returned 404 at `django-graphql-jwt.domake.io/llms.txt`. The docs site returned 200 but was not needed. PyPI JSON API used for the release dates.
