from __future__ import annotations

import dataclasses
import re
from inspect import cleandoc
from typing import Self

from undine.settings import undine_settings

__all__ = [
    "parse_description",
]


def parse_description(docstring: str | None) -> DocData:
    """Format the docstring of a function as a GraphQL description."""
    if not docstring:
        return DocData()
    return DocData.from_docstring(cleandoc(docstring).strip())


TRIM_PATTERN = re.compile(r"\s+")
STOP = r"(?=:param|:returns?|:raises?|:deprecated|$)"
RST_BODY = re.compile(rf"^(?P<text>.+?){STOP}.*", flags=re.DOTALL)
RST_PARAM = re.compile(rf":param (?P<name>\w+): (?P<text>.+?){STOP}", flags=re.DOTALL)
RST_RETURNS = re.compile(rf":returns?: (?P<text>.+?){STOP}", flags=re.DOTALL)
RST_RAISES = re.compile(rf":raises? (?P<name>\w+): (?P<text>.+?){STOP}", flags=re.DOTALL)
RST_DEPR = re.compile(rf":deprecated? (?P<name>\w+): (?P<text>.+?){STOP}", flags=re.DOTALL)


@dataclasses.dataclass
class DocData:
    body: str = ""
    arg_descriptions: dict[str, str] = dataclasses.field(default_factory=dict)
    return_description: str = ""
    raises_descriptions: dict[str, str] = dataclasses.field(default_factory=dict)
    deprecation_descriptions: dict[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_docstring(cls, docstring: str) -> Self:
        """Parse the docstring of a function as a GraphQL description."""
        if undine_settings.DOCSTRING_FORMAT == "reStructuredText":
            return cls.from_rst_docstring(docstring)
        if undine_settings.DOCSTRING_FORMAT == "plain":
            return cls.from_plain_docstring(docstring)

        msg = f"Unknown docstring format: '{undine_settings.DOCSTRING_FORMAT}'"
        raise ValueError(msg)

    @classmethod
    def from_rst_docstring(cls, docstring: str) -> Self:
        body: str = ""
        body_match = RST_BODY.search(docstring)
        if body_match is not None:
            body = body_match.group("text").strip()

        found_args = RST_PARAM.findall(docstring)
        arg_descriptions = {name: re.sub(TRIM_PATTERN, " ", text) for name, text in found_args}

        return_description: str = ""
        returns_match = RST_RETURNS.search(docstring)
        if returns_match is not None:
            return_description = re.sub(TRIM_PATTERN, " ", returns_match.group("text"))

        found_raises = RST_RAISES.findall(docstring)
        raises_descriptions = {key: re.sub(TRIM_PATTERN, " ", value) for key, value in found_raises}

        found_deprecations = RST_DEPR.findall(docstring)
        deprecation_descriptions = {key: re.sub(TRIM_PATTERN, " ", value) for key, value in found_deprecations}

        return cls(
            body=body,
            arg_descriptions=arg_descriptions,
            return_description=return_description,
            raises_descriptions=raises_descriptions,
            deprecation_descriptions=deprecation_descriptions,
        )

    @classmethod
    def from_plain_docstring(cls, docstring: str) -> Self:
        return cls(body=docstring)
