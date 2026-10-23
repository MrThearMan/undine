# WPGraphQL findings

Versions checked: `wp-graphql` v2.24.2 (2026-10-16). Monorepo `main` at `ddeaee8` (2026-10-16 commit, last push 2026-10-17).
WPGraphQL is a WordPress plugin. It is code-first: it builds the schema from WordPress data (post types, taxonomies, users, comments, menus, settings) and from PHP calls to a registry API (`register_graphql_*`). Almost all behavior can be changed with WordPress actions and filters.
The engine is webonyx/graphql-php (see `graphql-php.md`). This file does not repeat engine features.
PHP 7.4+. WordPress 6.0+. GPL-3.0.
Source is now a monorepo with four plugins: `plugins/wp-graphql` (core), `plugins/wp-graphql-smart-cache`, `plugins/wp-graphql-ide`, `plugins/wp-graphql-acf`. Also `websites/wpgraphql.com` (Next.js site source).
Docs source is in the repo: `plugins/wp-graphql/docs/*.md` (60 guides, about 520 KB), plus generated reference pages: `docs/functions/` (44), `docs/actions/` (50), `docs/filters/` (192), `docs/recipes/` (33). Each extension plugin has its own `docs/` folder.
No `llms.txt` or `llms-full.txt` on wpgraphql.com (404, HTML). No `.md` page variants (404).

## Maintenance status and ownership

- Very active. Many releases per month, managed by release-please, one tag per plugin (`wp-graphql/vX`, `wp-graphql-smart-cache/vX`, `wp-graphql-ide/vX`, `wp-graphql-acf/vX`).
- Core: v2.24.2 (2026-10-16), v2.24.1 (2026-10-15), v2.24.0 (2026-10-14), v2.23.1 (2026-09-22), v2.23.0 (2026-09-15). About 3800 stars, 119 open issues plus PRs.
- Smart Cache v2.3.3 (2026-10-14). IDE v5.6.0 (2026-09-16). WPGraphQL for ACF v3.0.0 (2026-09-08).
- Many security fixes in October 2026 (GHSA advisories): capability checks before target lookup in mutations, comment mutation leaks, user enumeration via password reset, SSRF checks for media upload by URL (internal IPv4/IPv6/NAT64 rejected), trashed content access.
- Ownership: WPGraphQL became a WordPress.org "Canonical Plugin" (announced 2024-10, https://wordpress.org/news/2024/10/wpgraphql/). README credits Automattic for support "as a canonical WordPress plugin". WP Engine funded early development (and sponsored Smart Cache and ACF). Gatsby is also credited.
- The GitHub repo is still `wp-graphql/wp-graphql`. It did not move to the `WordPress` GitHub org (`WordPress/wp-graphql` is 404). I think "canonical" means WordPress.org project status, not a repo transfer.
- Monorepo merge: Smart Cache imported in v2.8.0, IDE in v2.9.0, ACF in v2.10.0 (2026-03). Old repos `wp-graphql/wp-graphql-smart-cache` and `wp-graphql/wpgraphql-ide` are archived. `wp-graphql/wpgraphql-acf` is not archived yet. The older `wp-graphql/wp-graphql-acf` (pre-rewrite) is archived since 2024.
- Telemetry: opt-in Appsero insights, mirrored to `telemetry.wpgraphql.com` (v2.12.0).
- Repo is set up for AI agents (`AGENTS.md`, `CLAUDE.md` per plugin).

## New and upcoming

- v2.24.0: depth limiting on by default for new installs, `graphql_query_depth_max` filter. Security "settings review" wizard (`register_graphql_settings_review_step`). `publiclyQueryable` on `Taxonomy`.
- v2.21.0: request-level preview context, `X-GraphQL-Preview` header or `extensions.preview` in the request body.
- v2.18.0: setting groups are now `Node`s with an `id`. `template` (`ContentTemplateEnum`) and `isSticky` where args on post connections. `generalSettings.homeUrl`. Generated reference docs for hooks, functions and recipes.
- v2.17.0: `hour`, `minute`, `second` on `DateInput` (sub-day date filtering).
- v2.15.0: settings resolve outside wp-admin. v2.12.0: allowed additional hosts (`graphql_allowed_hosts`). v2.8.0: i18n.
- Experiments API (`src/Experimental`): opt-in features behind toggles. Shipped experiment: `EmailAddress` scalar and email fields using it (`EmailAddressScalarExperiment`, `EmailAddressScalarFieldsExperiment`).
- Branch `next` (16 commits ahead, 193 behind, last 2026-08-18): staging line for the next major.
- Branch `feat/wp-graphql-pqu` (2026-04): new plugin "WPGraphQL Persisted Query URLs" v0.1.0-beta.1. Persisted operations at GET paths like `/graphql/persisted/{queryHash}/variables/{variablesHash}`. Index from Smart Cache keys to URLs, so hosts with only URL purge can invalidate. Purge adapters (VIP, HTTP, null), custom stores, WP-CLI register. Needs Smart Cache.
- Branch `feat/hook-renames` (2026-07, 82 commits): hook naming audit, rename legacy hooks to `graphql_*` names with deprecation shims. `docs/generated/hooks-deprecated.md` and `hooks-naming-audit.md` already exist on `main`.
- Branch `experiment/abilities-under-the-hood` (2026-06): proof of concept that backs loaders and Model fields with the WordPress Abilities API, and generates an ability from a persisted query.
- Branch `refactor/next-wpgraphql-replace-faust`: website work (`wpgraphql-client`), not a plugin feature.

## Architecture and request pipeline

- HTTP endpoint from `Router` (`src/Router.php`). Default `/graphql`. Also `/index.php?graphql` without pretty permalinks. Path set in settings or `graphql_endpoint` filter. `graphql_get_endpoint()`, `graphql_get_endpoint_url()`.
- `GET` and `POST`. Mutations over `GET` are rejected by graphql-php. Content type checked (`graphql_is_valid_http_content_type`, `graphql_invalid_content_type_status_code`).
- Batch queries: JSON array of operations. On by default. Setting "Enable Batch Queries" and `graphql_is_batch_queries_enabled`. Batch limit setting "Batch Query Limit" (default 10). Action `graphql_execute_batch_queries`.
- PHP execution without HTTP: `graphql( [ 'query' => ..., 'variables' => ..., 'operation_name' => ... ] )`. Old `do_graphql_request()` still exists. Used for server-side rendering in themes and for tests.
- `Request` class builds the schema, `AppContext` and validation rules, then calls graphql-php. `AppContext` holds the viewer, the request and the DataLoaders (`get_loader( 'post' )`). Filter `graphql_app_context_config`.
- Schema is built per request. Only `RootQuery`/`RootMutation` are built eagerly. Other types are lazy through a type loader. Types with `eagerlyLoadType => true` are added for introspection only (types not reachable from roots).
- `is_graphql_request()`, `is_graphql_http_request()`: check if the current WP request is a GraphQL request.
- Response headers: `graphql_response_headers_to_send`, `graphql_response_status_code`, `graphql_send_nocache_headers`, CORS `graphql_access_control_allow_headers`. Allowed hosts for the endpoint: `graphql_allowed_hosts` (v2.12.0).
- Request data hooks: `graphql_request_data`, `graphql_execute_query_params`, `pre_graphql_execute_request` (short-circuit execution), `graphql_request_results`, `graphql_root_value`, `graphql_schema_config`.
- WP-CLI: `wp graphql generate-static-schema` writes the SDL to a file. `wp graphql settings-review` runs the security settings review (not in `wp-cli.md`).
- Multisite: one endpoint per site. Cross-site queries are not supported.
- Not supported in core: subscriptions, `@defer`/`@stream`, persisted queries (Smart Cache adds them), multipart file uploads (`createMediaItem` takes a URL or path in `filePath`), raw SQL, legacy widgets.

## Schema registry API

All functions are in `access-functions.php`. Call them in the `graphql_register_types` action (`get_graphql_register_action()` returns the right action name). Generated reference in `docs/functions/*.md`.

- `register_graphql_object_type( $name, $config )`, `register_graphql_interface_type`, `register_graphql_input_type`, `register_graphql_union_type`, `register_graphql_enum_type`, `register_graphql_scalar` (custom scalars, `serialize`/`parseValue`/`parseLiteral`), `register_graphql_type` (generic, takes `kind`).
- `register_graphql_field( $type, $name, $config )`, `register_graphql_fields( $type, $fields )`: add fields to any type, including core types.
- `register_graphql_connection( $config )`: add a Relay connection between two types. See "Connections".
- `register_graphql_mutation( $name, $config )`: add a Relay-style mutation. See "Mutations".
- `register_graphql_edge_field(s)( $from, $to, $name, $config )`: add fields to a connection edge type.
- `register_graphql_connection_where_arg(s)( $from, $to, $name, $config )`: add `where` args to a connection.
- `register_graphql_interfaces_to_types( $interfaces, $types )`: make existing types implement interfaces.
- `rename_graphql_field( $type, $old, $new )`, `rename_graphql_type( $old, $new )`.
- `deregister_graphql_type`, `deregister_graphql_field`, `deregister_graphql_connection`, `deregister_graphql_mutation`. Also filters `graphql_excluded_types`, `graphql_excluded_connections`, `graphql_excluded_mutations`.
- Name helpers: `graphql_format_name`, `graphql_format_field_name`, `graphql_format_type_name`, `is_valid_graphql_name`. Filter `graphql_pre_format_name`.
- Type config keys: `description` (string or callable, lazy), `fields` (array or callable), `interfaces`, `connections` (connections declared inline on the type), `eagerlyLoadType`, `resolveType` (interfaces/unions), `typeNames` (unions), `values` (enums), `kind`.
- Field config keys: `type`, `args`, `resolve( $source, $args, $context, $info )`, `description`, `deprecationReason`, `defaultValue` (args), `auth` (`callback`, `allowedCaps`, `allowedRoles`, `errorMessage`), `isPrivate` (needs a logged-in user), `allowFieldUnderscores`.
- Type modifiers in config: `'type' => [ 'non_null' => 'String' ]`, `[ 'list_of' => [ 'non_null' => 'Post' ] ]`. Lazy wrappers keep lazy loading.
- Interface field overrides: a type can redeclare an interface field. `TypeRegistry` checks structural compatibility (same wrapping, same or implementing base type). Not documented.
- Duplicate type or field names: registration is skipped and a `graphql_debug` message is added. It does not throw.
- Post types and taxonomies join the schema with `register_post_type`/`register_taxonomy` args: `show_in_graphql`, `graphql_single_name`, `graphql_plural_name`, `graphql_description`, `graphql_kind` (`object`, `interface`, `union`), `graphql_resolve_type`, `graphql_interfaces`, `graphql_exclude_interfaces`, `graphql_fields`, `graphql_exclude_fields`, `graphql_connections`, `graphql_exclude_connections`, `graphql_union_types`, `graphql_register_root_field`, `graphql_register_root_connection`, `graphql_exclude_mutations` (`create`, `update`, `delete`). Filters `register_graphql_post_type_args`, `register_graphql_taxonomy_args`.
- From each post type it generates: object type, root single field (`post(id:, idType:)`), root connection (`posts`), connections to terms and users, and `create*`/`update*`/`delete*` mutations.
- Default interfaces on post types (picked from `post_type_supports`): `Node`, `ContentNode`, `DatabaseIdentifier`, `UniformResourceIdentifiable`, `NodeWithTitle`, `NodeWithContentEditor`, `NodeWithAuthor`, `NodeWithFeaturedImage`, `NodeWithExcerpt`, `NodeWithComments`, `NodeWithRevisions`, `NodeWithPageAttributes`, `NodeWithTemplate`, `NodeWithTrackbacks`, `HierarchicalContentNode`, `Previewable`, `MenuItemLinkable`. Terms: `TermNode`, `HierarchicalTermNode`.
- Built-in data in the schema: posts, pages, media, revisions, categories, tags, custom post types and taxonomies, users, user roles, comments and comment authors, menus and menu items, plugins, themes, settings groups, enqueued scripts and stylesheets, content types and taxonomies as nodes, `viewer`.
- Root fields: `node`, `nodeByUri`, `contentNode`, `termNode`, `user`, `comment`, `menu`, `menuItem`, `plugin`, `theme`, `taxonomy`, `contentType`, `userRole`, `viewer`, `allSettings`, `generalSettings`, `readingSettings`, `writingSettings`, `discussionSettings`, plus one single field and one connection per post type and taxonomy.
- `nodeByUri( uri: )`: resolve any public URL (post, page, term archive, author archive, home page) to a node using WordPress rewrite rules (`NodeResolver`). Filters `graphql_pre_resolve_uri`, `graphql_resolve_uri`, `graphql_post_resolve_uri`.
- Field formats: content fields take `format: PostObjectFieldFormatEnum` (`RENDERED` default, `RAW` needs edit capability).
- Schema hooks: `graphql_register_initial_types`, `graphql_register_types`, `graphql_register_types_late`, `graphql_get_type_registry`, `graphql_schema`, `graphql_get_schema`.
- Per-type config filters: `graphql_wp_object_type_config`, `graphql_wp_interface_type_config`, `graphql_wp_union_type_config`, `graphql_wp_connection_type_config`, `graphql_wp_mutation_type_config`, `graphql_object_fields`, `graphql_interface_fields`, `graphql_input_fields`, `graphql_enum_values`, `graphql_field_definition`, `graphql_type_interfaces`, `graphql_union_possible_types`, `graphql_union_resolve_type`, `graphql_interface_resolve_type`, `graphql_custom_scalar_config`.
- Deprecation: `deprecationReason` on fields, args and enum values. Recipe "deprecating-a-field-in-the-schema".
- Schema lint in CI (`schema-linter.yml`). Not a user feature.

## Hooks (actions and filters)

- WordPress actions and filters are the main extension model. Reference pages: 50 actions, 192 filters (`docs/actions/`, `docs/filters/`). Generated from source docblocks with `@hookGroup` tags. Deprecated hooks list in `docs/generated/hooks-deprecated.md`.
- Lifecycle actions: `init_graphql_request`, `graphql_init`, `graphql_process_http_request`, `graphql_before_execute`, `graphql_execute`, `graphql_after_execute`, `graphql_return_response`, `graphql_process_http_request_response`, `graphql_response_set_headers`, `graphql_server_config`.
- Per-field middleware: `graphql_before_resolve_field` (action), `graphql_pre_resolve_field` (filter, short-circuits the resolver), `graphql_resolve_field` (filter the result), `graphql_after_resolve_field` (action). These wrap every field via `Utils\InstrumentSchema`. They get `$type_name` and `$field_key`, so callbacks filter by type and field themselves. There are no per-field hook names. Dynamic hooks exist only for field lists (`graphql_{$type_name}_fields`), connection field names (`graphql_wp_connection_{$from}_from_field_name`) and mutations (`graphql_insert_{$post_type}`, `graphql_update_{$taxonomy}`).
- Model hooks: `graphql_pre_model_data_is_private`, `graphql_data_is_private`, `graphql_model_prepare_fields`, `graphql_return_field_from_model`, `graphql_pre_return_field_from_model`, `graphql_after_return_field_from_model`, `graphql_return_modeled_data`, `graphql_model_field_capability`, `graphql_object_visibility`, `graphql_restricted_data_cap`.
- DataLoader hooks: `graphql_data_loaders`, `graphql_data_loader_classes`, `graphql_dataloader_pre_get_model`, `graphql_dataloader_get_model`, `graphql_dataloader_get_cached`, `graphql_dataloader_set_cached`.
- Connection hooks: `graphql_connection_args`, `graphql_connection_query_args`, `graphql_connection_pre_get_query`, `graphql_connection_query`, `graphql_connection_ids`, `graphql_connection_nodes`, `graphql_connection_edge(s)`, `graphql_connection_page_info`, `graphql_connection`, `graphql_connection_should_execute`, `graphql_connection_pre_should_execute`, `graphql_connection_is_valid_model`, `graphql_connection_default_query_amount`, `graphql_connection_max_query_amount`, `graphql_connection_query_class`, `graphql_connection_loader_name`, plus per-kind `graphql_post_object_connection_query_args` and `graphql_map_input_fields_to_wp_query` (and term, user, comment variants).
- Mutation hooks: `graphql_mutation_input`, `graphql_pre_mutate_and_get_payload`, `graphql_mutation_payload`, `graphql_mutation_response`, `graphql_insert_post_object`, `graphql_post_object_mutation_update_additional_data`, `graphql_post_object_mutation_set_object_terms`, `graphql_post_object_insert_post_args`, and the same set for terms, users, comments, media.
- Cursor hooks: `graphql_pre_post_cursor_node`, `graphql_post_object_cursor_meta_key`, `graphql_cursor_ordering_field`, `graphql_pre_wp_query_cursor_pagination_support`, `graphql_pre_wp_query_cursor_pagination_stability` (and term, user, comment variants).
- Recipes (`docs/recipes/`, 33): small copy-paste snippets. Examples: register a basic mutation, field with argument, connection to attached media, popular posts, make all users public, remove `extensions` from responses, fragments in PHP.

## Connections and pagination

- Relay Cursor Connections for all lists. Types `{From}To{To}Connection`, `{From}To{To}ConnectionEdge`, `{From}To{To}ConnectionPageInfo`. Fields `edges { cursor node }`, `nodes` (shortcut), `pageInfo { hasNextPage hasPreviousPage startCursor endCursor }`.
- Connection interfaces: `Connection`, `Edge`, `PageInfo`, `OneToOneConnection`, plus generated `{Type}Connection`, `{Type}ConnectionEdge` interfaces so clients can share fragments. `includeDefaultInterfaces => false` to skip them.
- Args: `first`, `last`, `after`, `before`, `where`. Default page size 10 (`graphql_connection_default_query_amount`). Max 100 (`graphql_connection_max_query_amount`). Larger requests are clamped to the max with a debug message, not an error.
- No `totalCount` in core. No offset pagination in core (the "WPGraphQL Offset Pagination" plugin is third-party). Docs list this as a known limit.
- Cursors: `base64( 'arrayconnection:' . $id )`. Cursor classes (`PostObjectCursor`, `TermObjectCursor`, `UserCursor`, `CommentObjectCursor`, `CursorBuilder`) translate the cursor into SQL `WHERE` clauses that keep the current `orderby` (including meta ordering), so pages are stable. Not in the guides.
- `register_graphql_connection` config: `fromType`, `toType`, `fromFieldName`, `resolve`, `connectionTypeName`, `connectionArgs`, `connectionFields`, `edgeFields`, `oneToOne` (single `node` edge, for example `author`), `auth`, `queryClass`, `connectionInterfaces`, `includeDefaultInterfaces`, `resolveCursor`, `deprecationReason`, `description`.
- Resolvers: subclass `AbstractConnectionResolver` and implement `loader_name()`, `prepare_query_args()`, `query()`, `get_ids_from_query()`, `is_valid_offset()`, optional `max_query_amount()`, `should_execute()`, `query_class()`. Built-ins: `PostObjectConnectionResolver`, `TermObjectConnectionResolver`, `UserConnectionResolver`, `CommentConnectionResolver`, `MenuItemConnectionResolver`, `PluginConnectionResolver`, `ThemeConnectionResolver`, `ContentTypeConnectionResolver`, `TaxonomyConnectionResolver`, `UserRoleConnectionResolver`, `EnqueuedScriptsConnectionResolver`.
- Resolver flow: the query returns only IDs. IDs go to the DataLoader for batched loads. Each node passes through the Model. Invalid or private models are dropped (`is_valid_model`).
- Guide for custom tables: `using-data-from-custom-database-tables.md` (custom loader, model, connection resolver).
- Code smell: `WPConnectionType` sets `resolve_cursor` only if `is_callable( $config['resolve'] )`, not `resolveCursor`. I think this is a small bug.

## `where` arguments (filtering and ordering)

- Each connection has a `where` input `{From}To{To}ConnectionWhereArgs`. These map to WordPress query classes (`WP_Query`, `WP_Term_Query`, `WP_User_Query`, `WP_Comment_Query`). Not a generic filter language. No `AND`/`OR` trees, except `dateQuery.relation`.
- Post where args: `search`, `id`, `in`, `notIn`, `name`, `nameIn`, `parent`, `parentIn`, `parentNotIn`, `title`, `hasPassword`, `password`, `status`, `stati`, `mimeType`, `dateQuery`, `orderby`, `isSticky` (v2.18), `template` (v2.18), `contentTypes` (on `contentNodes`). Author args `author`, `authorIn`, `authorNotIn`, `authorName` if the type supports authors. Category and tag args `categoryId`, `categoryIn`, `categoryName`, `categoryNotIn`, `tag`, `tagId`, `tagIn`, `tagNotIn`, `tagSlugAnd`, `tagSlugIn`.
- `dateQuery` (`DateQueryInput`): `year`, `month`, `week`, `day`, `hour`, `minute`, `second`, `after`/`before` (`DateInput`, sub-day since v2.17), `inclusive`, `column`, `compare`, `relation`.
- `orderby`: list of `{ field: PostObjectsConnectionOrderbyEnum, order: OrderEnum }`. Fields `AUTHOR`, `COMMENT_COUNT`, `DATE`, `IN`, `MENU_ORDER`, `MODIFIED`, `NAME_IN`, `PARENT`, `SLUG`, `TITLE`.
- Term where args: `cacheDomain`, `childless`, `childOf`, `descriptionLike`, `exclude`, `excludeTree`, `hideEmpty`, `hierarchical`, `include`, `name`, `nameLike`, `objectIds`, `order`, `orderby`, `padCounts`, `parent`, `search`, `slug`, `termTaxonomyId`, `updateTermMetaCache`.
- User where args: `exclude`, `include`, `hasPublishedPosts`, `login`, `loginIn`, `loginNotIn`, `nicename`, `nicenameIn`, `nicenameNotIn`, `role`, `roleIn`, `roleNotIn`, `search`, `searchColumns`, `orderby`.
- Comment where args: about 35, for example `authorIn`, `contentId`, `contentType`, `parent`, `status`, `includeUnapproved`, `karma`, `orderby`.
- No meta query or tax query in core. Third-party plugins add them (WPGraphQL Meta Query, WPGraphQL Tax Query). I think these are not maintained by the core team.
- Extend with `register_graphql_connection_where_arg` plus `graphql_map_input_fields_to_wp_query` (or `graphql_post_object_connection_query_args`) to map the new arg to query vars.

## Node and global ID model

- Relay Object Identification. Interface `Node { id: ID! }`. Root `node( id: ID! )` resolves any type.
- Global ID: `base64( "{loader}:{database_id}" )`, for example `base64( 'post:1' )`, `term:5`, `user:3`, `comment:9`. Built with `GraphQLRelay\Relay::toGlobalId` (`ivome/graphql-relay-php`). The loader prefix is the DataLoader name, not the GraphQL type name. So all post types share `post:`.
- `DatabaseIdentifier` interface adds `databaseId: Int!`. Many types also keep deprecated `{type}Id` fields.
- Single node root fields take `id` plus `idType` enum: `ID` (global), `DATABASE_ID`, `URI`, `SLUG` (non-hierarchical types). `URI` and `SLUG` for terms. Users: `ID`, `DATABASE_ID`, `URI`, `SLUG`, `EMAIL`, `USERNAME`.
- `nodeByUri` resolves a URL path to a node (see above). `UniformResourceIdentifiable` interface gives `uri`, `isContentNode`, `isTermNode`.
- Node type resolution: filter `graphql_resolve_node_type`.
- Settings groups are nodes since v2.18.0.

## Mutations

- Relay-style: one `input: {Name}Input!` argument, payload `{Name}Payload`. `clientMutationId` is added to input and payload automatically.
- `register_graphql_mutation( $name, [ 'inputFields' => ..., 'outputFields' => ..., 'mutateAndGetPayload' => fn( $input, $context, $info ) ] )`. `outputFields` resolvers receive the payload array.
- Built-in: `createPost`/`updatePost`/`deletePost` (and per post type), `createCategory`/`updateCategory`/`deleteCategory` (per taxonomy), `createUser`, `updateUser`, `deleteUser`, `registerUser`, `resetUserPassword`, `sendPasswordResetEmail`, `createComment`, `updateComment`, `deleteComment`, `restoreComment`, `createMediaItem`, `updateMediaItem`, `deleteMediaItem`, `updateSettings`. No login mutation in core (WPGraphQL JWT Authentication or Headless Login plugins add it).
- `deletePost` takes `forceDelete`. Post mutations can set terms by connection inputs (`categories: { nodes: [...], append: }`). `graphql_post_object_mutations_allow_term_creation` controls creating missing terms.
- Each mutation checks WordPress capabilities (`current_user_can`). Since 2.24.1 the capability check runs before the target lookup to avoid ID leaks.
- `createMediaItem` sideloads a file by URL or path (`filePath`). Protocols filter `graphql_media_item_create_allowed_protocols`. SSRF checks reject internal addresses. No multipart upload.
- Password reset rate limit per request: `graphql_allowed_password_reset_emails_per_request`.
- No nested writes beyond term assignment. No auto validation layer. Errors are thrown as `UserError`.

## Model layer and access control

- Every loaded WordPress object is wrapped in a Model (`src/Model/`): `Post`, `Term`, `User`, `Comment`, `CommentAuthor`, `Menu`, `MenuItem`, `Plugin`, `Theme`, `PostType`, `Taxonomy`, `UserRole`, `Avatar`, `SettingGroup`. Base class `WPGraphQL\Model\Model`.
- The Model maps WordPress names to GraphQL names (`post_content` to `content`) and holds field values as lazy closures.
- Object visibility: `get_visibility()` returns `public`, `restricted` or `private`. Private objects become `null` (single) or are removed from connections. Restricted objects return only `allowed_restricted_fields`. Checks consider login state, post status, owner and private post types.
- Field-level capability: Models declare capabilities per field (for example user `email` needs `list_users`). Filter `graphql_model_field_capability`. Denied fields resolve to `null`, not an error.
- Generated fields on every Model: `isPublic`, `isRestricted`, `isPrivate` (internal).
- Model hooks: `graphql_restricted_data_cap`, `graphql_pre_model_data_is_private`, `graphql_data_is_private`, `graphql_object_visibility`, `graphql_allowed_fields_on_restricted_type`, `graphql_model_prepare_fields`, `graphql_pre_return_field_from_model`, `graphql_return_field_from_model`, `graphql_html_entity_decoding_enabled`. Recipes: "make all users public", "filter to add restricted field on model".
- Schema-level field auth (separate from Models): field config `auth` (`callback`, `allowedCaps`, `allowedRoles`, `errorMessage`) and `isPrivate`. These throw `UserError`. Message filter `graphql_field_resolver_auth_error_message`.
- `show_in_graphql` controls exposure per post type and taxonomy. Docs say this differs from REST, which gates only on `show_in_rest`. `graphql_post_entities_allowed_post_types`, `graphql_term_entities_allowed_taxonomies`.
- Mutations check WordPress capabilities in each mutation class. No declarative permission classes.
- Docs guide for custom data: write a Model subclass with `is_private()` and `init()`.

## Authentication

- No login mutation or token issuing in core. Uses whatever WordPress auth is active.
- Cookie auth needs a nonce (`X-WP-Nonce` header or `_wpnonce` param, `graphql_get_nonce()`). No nonce means the request runs as a guest. Invalid nonce gives HTTP 403 "Cookie nonce is invalid". Filter `graphql_cookie_auth_require_nonce`. Requests with an `Authorization` header skip the nonce check.
- Application Passwords (WordPress core Basic auth) work. Official plugin WPGraphQL JWT Authentication (`wp-graphql/wp-graphql-jwt-authentication`, separate repo) adds `login` and `refreshJwtAuthToken` mutations. I did not check its status.
- Error hooks: `graphql_authentication_errors`, `graphql_authentication_error_status_code`.

## Security and limits

- "Only allow logged-in users" setting (`restrict_endpoint_to_logged_in_users`). Validation rule `RequireAuthentication`. Allow-list `graphql_require_authentication_allowed_fields` (recipe: allow a public login mutation).
- Introspection: `public_introspection_enabled`. Default on only for `local` and `development` environments (`wp_get_environment_type()`), off otherwise. Rule `DisableIntrospection`. Filter `graphql_introspection_keys`.
- Query depth: `QueryDepth` rule. Settings `query_depth_enabled`, `query_depth_max` (default 15). Settings default is off, but new installs get it on since v2.24.0 (seeded in `WPGraphQL.php`). Filter `graphql_query_depth_max`.
- No query complexity or cost analysis in core. Docs say depth does not limit width or aliases. The connection max of 100 is the only width cap.
- Batch: `batch_queries_enabled` (on), `batch_limit` (10).
- Custom validation rules: filter `graphql_validation_rules`.
- Settings review wizard (v2.24.0): admin walk-through of security settings in steps `access`, `request-limits`, `diagnostics`. Extend with `register_graphql_settings_review_step()`. Also `wp graphql settings-review`.
- CSRF: nonce checks for cookie auth. CORS headers via `graphql_access_control_allow_headers` and `graphql_response_headers_to_send`. No full CORS origin config in core.
- Allowed hosts filter `graphql_allowed_hosts` (v2.12.0).
- Security policy and GHSA advisories are used. Many fixes in 2026-09 and 2026-10.

## Settings

- Admin page "GraphQL > Settings". Stored in option `graphql_general_settings`. Read with `get_graphql_setting( $name, $default, $section )`.
- Core settings: `graphql_endpoint`, `restrict_endpoint_to_logged_in_users`, `batch_queries_enabled`, `batch_limit`, `query_depth_enabled`, `query_depth_max`, `query_analyzer_enabled`, `graphiql_enabled`, `show_graphiql_link_in_admin_bar`, `delete_data_on_deactivate`, `debug_mode_enabled`, `tracing_enabled`, `tracing_user_role`, `query_logs_enabled`, `query_log_user_role`, `public_introspection_enabled`.
- Constants: `GRAPHQL_DEBUG`, `GRAPHQL_EXPERIMENTAL_FEATURES`. Settings fields can be overridden by filters (`graphql_setting_field_value`, `graphql_get_setting_section_field_value`).
- Extensions add settings: `register_graphql_settings_section( $slug, $config )`, `register_graphql_settings_field( $group, $config )`, `register_graphql_settings_fields`. Fields support `depends_on`. Hooks `graphql_register_settings`, `graphql_init_settings`, `graphql_settings_sections`, `graphql_setting_field_config`.
- Admin notices API: `register_graphql_admin_notice`, `get_graphql_admin_notices`.
- Separate topic: WordPress site options in the schema. `register_setting( ..., [ 'show_in_graphql' => true ] )` exposes an option under `{group}Settings` and the flat `allSettings` type. `updateSettings` mutation writes them. `graphql_normalized_settings` filter exposes unregistered options. Per-setting keys: `graphql_capability`, `graphql_purge_all`, `graphql_field_name`, `graphql_readonly`, `graphql_resolve`. Allow lists `graphql_allowed_setting_groups`, `graphql_allowed_settings_by_group`.

## Debugging, tracing and logs

- Debug mode: setting `debug_mode_enabled` or constant `GRAPHQL_DEBUG`. Filter `graphql_debug_enabled`. Adds `extensions.debug` (array of messages) to responses, and adds error stack traces.
- `graphql_debug( $message, [ 'type' => ... ] )`: add a message to `extensions.debug` from any code. Core uses it for duplicate type names, clamped page sizes and so on. Filters `graphql_debug_log`, `graphql_debug_log_entry`.
- Tracing: `tracing_enabled`. Apollo-tracing-style `extensions.tracing` with `startTime`, `endTime`, `duration`, and per-resolver `path`, `parentType`, `fieldName`, `returnType`, `startOffset`, `duration`. Visible to `tracing_user_role` only. Filters `graphql_user_can_see_trace_data`, `graphql_tracing_response`.
- Query logs: `query_logs_enabled`. Needs `SAVEQUERIES`. `extensions.queryLog` with each SQL query, time and stack. Visible to `query_log_user_role`. Filters `graphql_user_can_see_query_logs`, `graphql_query_log_entry`.
- Recipes: log requests to the PHP error log, remove `extensions` from responses.
- Admin "Extensions" screen lists official and community extensions with install buttons (`graphql_get_extensions`).

## Query Analyzer

- `Utils\QueryAnalyzer`. Setting `query_analyzer_enabled`. Turned on automatically by Smart Cache. Filters `graphql_should_analyze_queries`, `graphql_should_analyze_query`.
- Before execution it walks the AST (parsed once since v2.19.0) and records: `list:{type}` for each list or connection of a node type, the query types and the Models used. During execution it tracks each loaded node ID through `graphql_dataloader_get_model`.
- Output header `X-GraphQL-Keys`: query hash, `graphql:Query`, `operation:{name}`, `list:post`, then global IDs of all loaded nodes. Limit 4000 bytes (`graphql_query_analyzer_header_length_limit`). Overflow keys are dropped and summarized as `skipped:{type}`. Also `X-GraphQL-Query-ID`.
- `extensions.queryAnalyzer` (when shown to the user, `graphql_should_show_query_analyzer_in_extensions`) lists keys, skipped keys and counts.
- Purpose: tag-based cache invalidation at the CDN or host. Smart Cache uses it.
- Filters: `graphql_query_analyzer_graphql_keys`, `graphql_query_analyzer_get_headers`, `graphql_query_analyzer_runtime_node`, `graphql_query_analyzer_get_runtime_nodes`, `graphql_pre_query_analyzer_get_list_types`, `graphql_query_id_hash_algorithm`.

## Caching and DataLoaders

- DataLoaders (`src/Data/Loader/`) batch by ID per request: `PostObjectLoader`, `TermObjectLoader`, `UserLoader`, `CommentLoader`, `CommentAuthorLoader`, `PluginLoader`, `ThemeLoader`, `PostTypeLoader`, `TaxonomyLoader`, `UserRoleLoader`, `SettingGroupLoader`, enqueued asset loaders. Base `AbstractDataLoader` with `loadKeys()` (abstract), `buffer()`, `load_deferred()`, `load()`, `load_many()`, `prime()`, `clear()`, `clear_all()`, `get_model()`. Results are wrapped in graphql-php `Deferred`.
- Loaders run one batched WordPress query per type (for example one `WP_Query` with `post__in` and `no_found_rows`). That query fills the WordPress object cache, then each item is read from it. Register custom loaders with `graphql_data_loader_classes`.
- No response cache in core. Core sends no-cache headers for authenticated requests (`graphql_send_nocache_headers`). `GET` requests can be cached by the host.
- Smart Cache plugin adds caching (see below).

## Experiments

- Opt-in feature flags for proposed core features (`src/Experimental`). Admin "Experiments" screen, constant `GRAPHQL_EXPERIMENTAL_FEATURES` (array or `false`), filter `graphql_experimental_features_override`.
- API: subclass `AbstractExperiment` with `slug()`, `config()` (title, description, dependencies), `init()`. Register with `graphql_experiments_registered_classes`. Experiments can depend on other experiments (required or optional).
- Active experiments are listed in `extensions` in debug mode. Capability filter `graphql_experimental_features_cap`.
- Current experiment: `EmailAddress` scalar plus email fields typed with it.
- Docs: `experiments.md`, `experiments-using.md`, `experiments-creating.md`, `experiments-contributing.md`.

## Previews and other features

- Request-level preview (v2.21.0): `X-GraphQL-Preview` header (RFC 8941 structured field dictionary, for example `id`, `nonce`) or `extensions.preview` in the body. Not supported per operation in batches. Old `asPreview` argument is deprecated. ACF fields also preview.
- Hierarchical data: `parent`, `children`, `ancestors` connections. Guide `hierarchical-data.md`.
- Menus: `menus`, `menuItems`, `MenuLocationEnum`. Menus are private unless assigned to a location. Recipe "making menus and menu items public".
- Enqueued assets: `enqueuedScripts`, `enqueuedStylesheets` on nodes (v2.20.0 filter by handle).
- Templates: `ContentTemplate` interface and `template` where arg.
- Auto-updates control: `wpgraphql_enable_major_autoupdates`, `wpgraphql_enable_untested_autoupdates` (major releases are gated for compatibility).
- Testing docs: `testing.md`. Uses Codeception and wp-browser. `wp-graphql/wp-graphql-testcase` provides `WPGraphQLTestCase` with `assertQuerySuccessful`, `expectedField`, `expectedNode` (used in core tests).
- `compatibility-guide.md` and `upgrading.md`: semver policy, breaking changes only in majors, deprecations kept for a while.

## Official extensions

### WPGraphQL Smart Cache (`plugins/wp-graphql-smart-cache`, v2.3.3)

- Network cache: makes `GET` responses cacheable at the host or CDN. Uses Query Analyzer `X-GraphQL-Keys` as cache tags. Setting "Cache-Control max-age" (default 600 s).
- Object cache: stores responses in the WordPress object cache (Redis, Memcached), for `POST` too. Settings to enable, set TTL, and "Purge Cache Now". Storage backends `WpCache`, `Transient`, `Ephemeral`.
- Invalidation: listens to WordPress events and fires `graphql_purge( $key, $event )`. Publish purges `list:{type}`. Update or unpublish purges the node global ID plus `skipped:{type}`. "Purge all" fires `graphql:Query`. Hooks `wpgraphql_cache_purge_all`, `wpgraphql_cache_purge_nodes`, `graphql_cache_invalidation_init`. Settings with `graphql_purge_all` purge everything.
- Hosts must implement tag purge from `graphql_purge`. Docs name WP Engine and LiteSpeed. "On-demand revalidation" guide shows a webhook to a Next.js front end.
- Persisted queries: private post type `graphql_document`. Request with `queryId` (hash or alias). Slug is the SHA-256 of the document. Unknown IDs return `PersistedQueryNotFound`. I think this matches the Apollo APQ handshake (code comments call it "automatic persisted query path"). Auto-saved documents from logged-out visitors are capped. Garbage collection by age.
- Per document: alias names, allow/deny grant, max-age, description, groups. Mutations `createGraphqlDocument`, `updateGraphqlDocument`. Query `graphqlDocument`.
- Allow/deny mode (setting "Saved Queries"): "Allow only specific queries" locks public users to allow-listed documents (`AllowDenyQueryDocument` validation rule). "Deny some specific queries" blocks listed ones.
- WP-CLI: documents `audit` and `purge` subcommands.
- Upcoming: "Persisted Query URLs" plugin on branch `feat/wp-graphql-pqu` (see "New and upcoming").

### WPGraphQL IDE (`plugins/wp-graphql-ide`, v5.6.0)

- Replaces the old GraphiQL page in wp-admin (legacy GraphiQL still in core, `graphiql_enabled`, `enqueue_graphiql_extension`, docs `wp-graphiql.md`, `customizing-wpgraphiql.md`).
- v5.0 is a rewrite on `@wordpress/components` and CodeMirror 6. Tabs with auto-save, schema-aware autocomplete and lint, docs explorer, response views (Formatted, Table, Raw), tabs for `debug`, `queryAnalyzer`, `tracing`, `queryLog` extensions, history per user, visual query composer, auth toggle (run as current user or public).
- Saved queries, collections and share links need Smart Cache (`graphql_document`).
- Extensible: activity bar panels, response panels, status bar items, execute lifecycle hooks, `@wordpress/data` stores, PHP `register_graphql_document_setting_field`. Bundled panels: help, query composer, Smart Cache.

### WPGraphQL for ACF (`plugins/wp-graphql-acf`, v3.0.0)

- Exposes Advanced Custom Fields field groups. Per group and field settings `show_in_graphql`, `graphql_field_name`, `graphql_types` (or `map_graphql_types_from_location_rules`).
- Field groups become types (interface `AcfFieldGroup`, `WithAcf{Group}` interfaces on the target types). About 45 field types, including repeater, flexible content, clone, relationship, ACF Pro and ACF Extended types.
- ACF options pages (`AcfOptionsPage`). ACF-registered post types and taxonomies. Previews.
- `register_graphql_acf_field_type( $acf_type, $config )` for third-party ACF field types.
- v3.0.0 breaking: options pages need explicit `show_in_graphql`.

### Other related plugins (outside the monorepo)

- WPGraphQL JWT Authentication (`wp-graphql/wp-graphql-jwt-authentication`): v0.7.2 (2026-03-13). `login`, `refreshJwtAuthToken` mutations.
- WPGraphQL WooCommerce (`wp-graphql/wp-graphql-woocommerce`): active (push 2026-06). Community maintained under the same org.
- WPGraphQL Content Blocks (`wpengine/wp-graphql-content-blocks`): block editor data. Maintained by WP Engine. Active.
- `wp-graphql/wp-graphql-testcase`: PHPUnit/Codeception test helpers. Last push 2024-08.

## Docs and code disagreements

- `security.md` and the settings field say query depth limiting defaults to off. New installs since v2.24.0 get it on (`WPGraphQL.php` seeds `query_depth_enabled => 'on'`). Existing installs keep off.
- `known-limitations.md` links to a "Pagination Guide" at `/docs/pagination/`. There is no such page in `docs/`.
- `known-limitations.md` lists Pantheon as a Smart Cache host with "(I believe)". Not confirmed.
- `WPConnectionType` reads `resolveCursor` only when `resolve` is callable. See "Connections".
- The `wp-cli.md` guide covers `generate-static-schema` only. `settings-review` exists in code.
- `authentication-and-authorization.md`/`security.md` still list old REST plugins (Basic-Auth, OAuth1) as options.

## Sources

- Repo: https://github.com/wp-graphql/wp-graphql (shallow clone of `main`, 2026-10-17)
- Core docs source: `plugins/wp-graphql/docs/` (rendered at https://www.wpgraphql.com/docs/introduction)
- Function reference: https://www.wpgraphql.com/functions (source `docs/functions/`)
- Actions and filters reference: https://www.wpgraphql.com/actions, https://www.wpgraphql.com/filters (source `docs/actions/`, `docs/filters/`)
- Recipes: https://www.wpgraphql.com/recipes (source `docs/recipes/`)
- Changelogs: `plugins/*/CHANGELOG.md`, https://github.com/wp-graphql/wp-graphql/releases
- Smart Cache docs: `plugins/wp-graphql-smart-cache/docs/`
- IDE docs: `plugins/wp-graphql-ide/README.md`, `UPGRADE-5.0.md`, `docs/`
- ACF docs: `plugins/wp-graphql-acf/docs/`
- Canonical plugin announcement: https://wordpress.org/news/2024/10/wpgraphql/
- Branches checked via GitHub API: `next`, `feat/wp-graphql-pqu`, `feat/hook-renames`, `experiment/abilities-under-the-hood`
- https://www.wpgraphql.com/llms.txt and `/llms-full.txt`: 404
