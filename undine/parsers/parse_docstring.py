from __future__ import annotations

import ast
import inspect
import re
from functools import cache
from inspect import cleandoc
from textwrap import dedent

from undine.exceptions import InvalidDocstringParserError
from undine.settings import undine_settings
from undine.typing import DocstringParserProtocol

__all__ = [
    "docstring_parser",
    "parse_class_attribute_docstrings",
]


class PreProcessingDocstringParser:
    """
    A docstring parser that implements another parser with
    pre-processing steps for null-checking and input sanitation operations.
    """

    def __init__(self, parser_impl: type[DocstringParserProtocol]) -> None:
        if not isinstance(parser_impl, DocstringParserProtocol):
            raise InvalidDocstringParserError(cls=parser_impl)

        self.parser_impl = parser_impl

    def parse_body(self, docstring: str | None) -> str | None:
        if docstring is None:
            return None
        docstring = cleandoc(docstring).strip()
        return self.parser_impl.parse_body(docstring)

    def parse_arg_descriptions(self, docstring: str | None) -> dict[str, str]:
        if docstring is None:
            return {}
        docstring = cleandoc(docstring).strip()
        return self.parser_impl.parse_arg_descriptions(docstring)

    def parse_return_description(self, docstring: str | None) -> str | None:
        if docstring is None:
            return None
        docstring = cleandoc(docstring).strip()
        return self.parser_impl.parse_return_description(docstring)

    def parse_raise_descriptions(self, docstring: str | None) -> dict[str, str]:
        if docstring is None:
            return {}
        docstring = cleandoc(docstring).strip()
        return self.parser_impl.parse_raise_descriptions(docstring)

    def parse_deprecations(self, docstring: str | None) -> dict[str, str]:
        if docstring is None:
            return {}
        docstring = cleandoc(docstring).strip()
        return self.parser_impl.parse_deprecations(docstring)


class RSTDocstringParser:
    """A docstring parser for reStructuredText formatted docstrings."""

    TRIM_PATTERN = re.compile(r"\s+")
    STOP_PATTERN = r"(?=:param|:returns?|:raises?|:deprecated?|$)"
    BODY_PATTERN = re.compile(rf"^(?P<text>.+?){STOP_PATTERN}.*", flags=re.DOTALL)
    PARAM_PATTERN = re.compile(rf":param (?P<name>\w+): (?P<text>.+?){STOP_PATTERN}", flags=re.DOTALL)
    RETURN_PATTERN = re.compile(rf":returns?: (?P<text>.+?){STOP_PATTERN}", flags=re.DOTALL)
    RAISE_PATTERN = re.compile(rf":raises? (?P<name>\w+): (?P<text>.+?){STOP_PATTERN}", flags=re.DOTALL)
    DEPR_PATTERN = re.compile(rf":deprecated? (?P<name>\w+): (?P<text>.+?){STOP_PATTERN}", flags=re.DOTALL)

    @classmethod
    def parse_body(cls, docstring: str) -> str:
        body: str = ""
        body_match = cls.BODY_PATTERN.search(docstring)
        if body_match is not None:
            body = body_match.group("text").strip()
        return body

    @classmethod
    def parse_arg_descriptions(cls, docstring: str) -> dict[str, str]:
        found_args = cls.PARAM_PATTERN.findall(docstring)
        return {name: re.sub(cls.TRIM_PATTERN, " ", text).strip() for name, text in found_args}

    @classmethod
    def parse_return_description(cls, docstring: str) -> str:
        return_description: str = ""
        returns_match = cls.RETURN_PATTERN.search(docstring)
        if returns_match is not None:
            return_description = re.sub(cls.TRIM_PATTERN, " ", returns_match.group("text")).strip()
        return return_description

    @classmethod
    def parse_raise_descriptions(cls, docstring: str) -> dict[str, str]:
        found_raises = cls.RAISE_PATTERN.findall(docstring)
        return {key: re.sub(cls.TRIM_PATTERN, " ", value).strip() for key, value in found_raises}

    @classmethod
    def parse_deprecations(cls, docstring: str) -> dict[str, str]:
        found_deprecations = cls.DEPR_PATTERN.findall(docstring)
        return {key: re.sub(cls.TRIM_PATTERN, " ", value).strip() for key, value in found_deprecations}


class PlainDocstringParser:
    """
    A docstring parser for plain docstrings.
    Parses the body as is and leaves everything else alone.
    """

    @classmethod
    def parse_body(cls, docstring: str) -> str:
        return docstring.strip()

    @classmethod
    def parse_arg_descriptions(cls, docstring: str) -> dict[str, str]:
        return {}

    @classmethod
    def parse_return_description(cls, docstring: str) -> str:
        return ""

    @classmethod
    def parse_raise_descriptions(cls, docstring: str) -> dict[str, str]:
        return {}

    @classmethod
    def parse_deprecations(cls, docstring: str) -> dict[str, str]:
        return {}


docstring_parser = PreProcessingDocstringParser(parser_impl=undine_settings.DOCSTRING_PARSER)


@cache
def parse_class_attribute_docstrings(cls: type, /) -> dict[str, str]:
    """
    Parse class attribute docstrings from the given class.

    >>> class Foo:
    ...     bar: int = 1
    ...     '''Description.'''
    ...
    ...     baz: int = 2
    ...     '''Another description.'''
    >>>
    >>> parse_class_attribute_docstrings(Foo)
    {'bar': 'Description.', 'baz': 'Another description.'}
    """
    descriptions: dict[str, str] = {}

    try:
        module = ast.parse(dedent(inspect.getsource(cls)))
    except OSError:  # Classes created with `type(...)` don't have a source.
        return descriptions

    class_def: ast.ClassDef = module.body[0]

    name: str | None = None
    for expr in class_def.body:
        # Variable docstrings are always directly below the class variable definition.
        if name is not None:
            if isinstance(expr, ast.Expr) and isinstance(expr.value, ast.Constant):
                descriptions[name] = inspect.cleandoc(expr.value.value)
            name = None
            continue

        if isinstance(expr, ast.AnnAssign):
            name = expr.target.id
        elif isinstance(expr, ast.Assign):
            name = expr.targets[0].id

    return descriptions
