# graphene-pydantic findings

Version checked: 0.6.1 (PyPI, 2024-02-01). Last commit on `master`: 2025-01-13. No release since 0.6.1. PyPI classifier is "Development Status :: 3 - Alpha".
Package `graphene-pydantic`. Import `graphene_pydantic`. Depends on `graphene>=2.1.8` and `pydantic>=2.0`. Supports Graphene 2 and 3 (`GRAPHENE2` switch in `converters.py`). Python 3.8 to 3.12.
Very small codebase (about 870 lines in 5 modules). Public exports: `PydanticObjectType`, `PydanticInputObjectType`. `Registry` and `get_global_registry` are importable from `graphene_pydantic.registry`.
No docs site and no `docs/` directory. The README is the only user documentation. No `CHANGELOG.md`. GitHub releases only go to 0.3.0 and mostly have no notes.
It only maps Pydantic models to Graphene types. Not tied to Django or any ORM. No HTTP view, no settings.

## Output types (`PydanticObjectType`)

- `class Person(PydanticObjectType): class Meta: model = PersonModel`. Builds one `graphene.Field` per entry in `model.model_fields`.
- `Meta.only_fields` and `Meta.exclude_fields` (tuples). Setting both raises `ValueError`.
- `Meta.registry=Registry(...)` for a non-global registry. `Meta.skip_registry=True` to not register the type. Default is one global registry per base class (`get_global_registry(PydanticObjectType)`).
- `Meta.interfaces` is passed to Graphene. Nothing is generated from it. A TODO in `objecttype.py` says interfaces are not handled.
- Type description comes from the model docstring if the Graphene class has none.
- Field description comes from `Field(description=...)`. No docstring or attribute doc parsing.
- `Field(alias=...)` sets the GraphQL field name on output types only. Input types ignore the alias.
- Default resolver is `getattr(root, name, None)`. A `resolve_<name>` method on the class is used instead if present.
- Extra fields can be declared by hand on the class with normal Graphene fields and resolvers.
- No per-field override of generated fields. The code has a "TODO: implement an OverrideField" note.
- Auto `is_type_of`: `isinstance(root, Meta.model)`. README still says to write `is_type_of` by hand for unions.
- Pydantic computed fields (`@computed_field`) are not mapped. Only `model_fields` is read. I think `model_computed_fields` is ignored.
- No Relay `Node`, connections or pagination helpers. The user can add `relay.Node` through `interfaces` and write it by hand.

## Input types (`PydanticInputObjectType`)

- Same `Meta` options as the output type: `model`, `only_fields`, `exclude_fields`, `registry`, `skip_registry`.
- Uses `field.is_required()`, `field.default` as `default_value`, and `field.description`.
- No automatic Pydantic validation. The resolver gets a Graphene input object. The user calls `Model.model_validate(data)` or `TypeAdapter(Model).validate_python(data)` by hand (see `tests/test_graphene.py`).
- No conversion of Pydantic `ValidationError` into GraphQL errors. No error-shape mapping. Validators (`field_validator`, `model_validator`) only run when the user validates by hand.
- No constraint reflection. `Field(gt=, max_length=, pattern=)` are not shown in the schema.
- No mutation class. The user writes `graphene.Mutation` with `class Arguments`.
- Union fields in inputs are meant to be skipped. I think this check is broken: `construct_fields` in `inputobjecttype.py` tests `isinstance(annotation, str) or isinstance(annotation, int)`, which is never true for a type. README says input unions fail with a Graphene error.

## Type mapping (`converters.find_graphene_type`)

- `str`, `bytes` to `String`. `int` to `Int`. `float` to `Float`. `bool` to `Boolean`. `uuid.UUID` to `UUID`. `datetime`, `date`, `time` to `DateTime`, `Date`, `Time`. `Decimal` to Graphene `Decimal` (or `Float` if missing).
- Plain `dict` to `JSONString`. `Dict[K, V]` and other mappings raise `ConversionError("Don't know how to handle mappings in Graphene.")`.
- `bson.ObjectId` to `ID` when `bson` is installed.
- `enum.Enum` subclasses to `graphene.Enum.from_enum(...)`. A new Graphene enum per field. I think two fields with the same enum make duplicate types.
- `List`, `Set`, `Tuple`, `Sequence`, `Iterable`, `Collection` to `List(inner)`. Only the first type argument is used. Heterogeneous tuples lose their other types.
- `Optional[T]` and `T | None` to nullable `T`. Nullability comes from `is_required()` plus default handling.
- `Union[A, B]` and `A | B` to a generated `graphene.Union` named `UnionOf<A><B>`. Order matters. The subclass must come first or objects resolve to the base type (README).
- `Literal[...]` to the scalar of its value type. Mixed value types make a `graphene.Union` of scalars. I think this schema is invalid, because GraphQL unions only take object types.
- Nested Pydantic models map to their registered `PydanticObjectType`. Unregistered models get a `Placeholder`.
- Subclasses of basic types (for example `str` subclasses) fall back to the base scalar through `issubclass`.
- Unknown types raise `ConversionError`. No extension hook or custom type map. The user must `exclude_fields` and add the field by hand.
- No support for Pydantic special types (`EmailStr`, `HttpUrl`, `SecretStr`, `conint`). I think `Annotated` types work only when the inner type is plain, because the annotation is read from `FieldInfo.annotation` after Pydantic strips the metadata.
- No custom scalars are defined by the library.

## Forward references and circular models

- `Model.resolve_placeholders()`: must be called on each type after all types exist. Replaces `Placeholder` fields with the real Graphene types.
- String forward refs are evaluated in the module of the model (`evaluate_forward_ref`).
- Self-referencing models work after `resolve_placeholders()` (`tests/test_converters.py::test_self_referencing`).
- I think `PydanticInputObjectType.resolve_placeholders()` is broken. It calls `registry.register_object_field(..., model=...)`, but that method takes no `model` argument.

## Registry

- `Registry(required_obj_type)`: maps Pydantic model to Graphene type and keeps the source `FieldInfo` per field. `get_type_for_model`, `get_object_field_for_graphene_field`, `add_placeholder_for_model`.
- `reset_global_registry(obj_type)` for tests.
- One model can have only one registered output type per registry. A second type for the same model overwrites the first.

## Areas not supported

- Query optimization, batching, dataloaders: not in scope.
- Filtering, ordering, pagination, connections: not supported.
- Permissions, authentication, visibility: not supported.
- Automatic mutations, validation on input, error mapping: not supported.
- Interfaces from model inheritance: not supported. Model inheritance only copies fields.
- Subscriptions, file uploads, directives, federation: not supported. These come from Graphene.
- Settings system: none.
- Documentation site and API reference: none.

## Sources

Repo: https://github.com/graphql-python/graphene-pydantic (shallow clone at `/tmp/graphene-pydantic`, `master`, last commit 2025-01-13).

Docs read:
- `README.md` (the only user docs)
- `examples/departments.py`
- No `docs/` directory in the repo. No docs site is listed.

Changelog:
- No `CHANGELOG.md` in the repo.
- GitHub releases (only to 0.3.0): https://github.com/graphql-python/graphene-pydantic/releases (read through https://api.github.com/repos/graphql-python/graphene-pydantic/releases)
- PyPI release dates: https://pypi.org/pypi/graphene-pydantic/json

Source files checked:
- `graphene_pydantic/__init__.py`, `objecttype.py`, `inputobjecttype.py`, `converters.py`, `registry.py`, `util.py`
- `tests/test_converters.py`, `tests/test_graphene.py`, `tests/test_forward_refs.py`, `tests/test_objecttype.py`, `tests/test_inputobjecttypes.py`, `tests/test_registry.py`
- `pyproject.toml`
