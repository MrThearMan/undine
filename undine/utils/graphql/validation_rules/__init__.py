from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from graphql import NoSchemaIntrospectionCustomRule, specified_rules

from undine.settings import undine_settings
from undine.typing import DjangoRequestProtocol

from .max_alias_count import MaxAliasCountRule
from .max_complexity_rule import MaxComplexityRule
from .max_directive_count import MaxDirectiveCountRule
from .max_list_nesting_depth import MaxListNestingDepthRule
from .visibility_rule import VisibilityRule

if TYPE_CHECKING:
    from graphql import ASTValidationRule


__all__ = [
    "DjangoRequestProtocol",
    "get_validation_rules",
]


def get_validation_rules(*, inside_request: bool = False) -> tuple[type[ASTValidationRule], ...]:
    """Get the GraphQL validation rules based on project current settings."""
    schema = undine_settings.SCHEMA
    visibility_active = bool(schema.extensions.get(undine_settings.VISIBILITY_ACTIVE_EXTENSIONS_KEY, False))
    visibility_enabled = inside_request and visibility_active
    return tuple(
        itertools.chain(
            specified_rules,
            [MaxAliasCountRule, MaxDirectiveCountRule, MaxComplexityRule, MaxListNestingDepthRule],
            [] if not visibility_enabled else [VisibilityRule],
            [] if undine_settings.ALLOW_INTROSPECTION_QUERIES else [NoSchemaIntrospectionCustomRule],
            undine_settings.ADDITIONAL_VALIDATION_RULES,
        )
    )
