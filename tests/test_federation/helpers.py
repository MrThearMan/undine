from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import DirectiveDefinitionNode, DirectiveNode, ListValueNode, StringValueNode, Visitor, visit

if TYPE_CHECKING:
    from graphql import DocumentNode

__all__ = [
    "render_compatibility_schema",
    "undefined_directive_usages",
]


# Directives that a subgraph schema can use without defining or importing them.
IMPLICITLY_AVAILABLE_DIRECTIVES = frozenset({"deprecated", "include", "link", "oneOf", "skip", "specifiedBy"})


def render_compatibility_schema(undine_settings: Any) -> str:
    """Render the products subgraph SDL using the compatibility project's own settings."""
    # Two passes are required to ensure that imported settings can see the overrides.
    from config.settings import UNDINE as PRODUCT_SCHEMA_SETTINGS  # type: ignore[import-not-found]  # noqa: PLC0415

    for key, value in PRODUCT_SCHEMA_SETTINGS.items():
        setattr(undine_settings, key, value)
    for key, value in PRODUCT_SCHEMA_SETTINGS.items():
        setattr(undine_settings, key, undine_settings.make_imports(key, value))

    from products.management.commands.export import render_schema  # type: ignore[import-not-found]  # noqa: PLC0415

    return render_schema()


def undefined_directive_usages(document: DocumentNode) -> set[str]:
    """Names of the directives that the document uses but does not make available."""
    available = IMPLICITLY_AVAILABLE_DIRECTIVES | _defined_directives(document) | _imported_directives(document)
    return _used_directives(document) - available


def _used_directives(document: DocumentNode) -> set[str]:
    visitor = _DirectiveUsageVisitor()
    visit(document, visitor)
    return visitor.names


def _defined_directives(document: DocumentNode) -> set[str]:
    return {
        definition.name.value for definition in document.definitions if isinstance(definition, DirectiveDefinitionNode)
    }


def _imported_directives(document: DocumentNode) -> set[str]:
    visitor = _LinkImportVisitor()
    visit(document, visitor)
    return visitor.names


class _DirectiveUsageVisitor(Visitor):
    def __init__(self) -> None:
        super().__init__()
        self.names: set[str] = set()

    def enter_directive(self, node: DirectiveNode, *args: Any) -> None:
        self.names.add(node.name.value)


class _LinkImportVisitor(Visitor):
    def __init__(self) -> None:
        super().__init__()
        self.names: set[str] = set()

    def enter_directive(self, node: DirectiveNode, *args: Any) -> None:
        if node.name.value != "link":
            return

        for argument in node.arguments:
            if argument.name.value != "import":
                continue
            if not isinstance(argument.value, ListValueNode):
                continue

            for value in argument.value.values:
                if isinstance(value, StringValueNode):
                    self.names.add(value.value.removeprefix("@"))
