# Mypy plugin development

## Incremental cache safety

Plugin hooks are cached across daemon runs, so they must not depend on global state or on
mypy AST attributes that aren't serialized.

`info.defn.*` (`ClassDef.keywords`, `.decorators`, `.metaclass`, `.defs`, `.analyzed`) is a
common trap. It's populated only during fresh analysis and reads as empty on cache-loaded
`TypeInfo`s (see `mypy/nodes.py::ClassDef.serialize`), silently corrupting downstream checks.

Persist anything you need across runs into `TypeInfo.metadata` (a `dict[str, JsonDict]`
reserved for plugins and always serialized). Populate it during the fresh-analysis
`base_class_hook`, then read from metadata everywhere else. This is the same pattern
mypy's own `attrs` and `dataclasses` plugins use.

## Debugging hooks

When a hook seems not to fire, add `print(f"...", file=sys.stderr)` inside it and
run mypy once. Mypy captures plugin stderr and shows it inline in the error output.
Via pytest-mypy-plugins the print lines appear as spurious "diff" lines, which is
convenient for confirming the hook ran.

To see the type mypy resolved for an expression, temporarily swap `assert_type(x, ...)`
for `reveal_type(x)`.
