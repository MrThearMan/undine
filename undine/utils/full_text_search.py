from __future__ import annotations

import dataclasses
import re
import unicodedata
import urllib.parse
from collections import UserString
from typing import TYPE_CHECKING, Unpack

from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models import Q
from django.utils.translation import get_language_from_path, get_language_from_request

from undine.settings import undine_settings

from .reflection import get_members

if TYPE_CHECKING:
    from undine import Filter
    from undine.typing import FTSLang, GQLInfo, LangCode, LangSep, PostgresFTSLangSpecificFields

__all__ = [
    "PostgresFTS",
]


class PostgresFTS:
    """
    Filter reference for Postgres full text search.

    Creates a SearchVector for the request language, annotates it to the queryset,
    and searches using a raw search string created using the `build_pg_search` function.
    """

    def __init__(
        self,
        *common: str,
        separator: LangSep = "|",
        **lang_specific: Unpack[PostgresFTSLangSpecificFields],
    ) -> None:
        """
        Postgres full text search filter reference.

        :param common: Common fields for all languages.
        :param separator: Separator for each search term in the query.
        :param lang_specific: Fields specific to each language.
        """
        self.separator = separator
        self.vectors: dict[FTSLang, SearchVector] = {
            lang: SearchVector(*set(*common, *fields), config=lang)  # type: ignore[misc]
            for lang, fields in lang_specific.items()
        }

    def get_search_language(self, info: GQLInfo) -> SearchLanguage:
        lang = get_request_search_language(info)
        if lang not in self.vectors:
            return TextSearchLang.ENGLISH
        return lang

    def get_vector_alias_key(self, ftr: Filter, lang: SearchLanguage) -> str:
        return f"{undine_settings.PG_TEXT_SEARCH_PREFIX}_{ftr.name}_{lang.name}"


@dataclasses.dataclass(frozen=True, slots=True)
class PostgresFTSExpressionResolver:
    """Resolves a filter using a Postgres full text search."""

    fts: PostgresFTS

    def __call__(self, root: Filter, info: GQLInfo, *, value: str) -> Q:
        lang = self.fts.get_search_language(info)
        key = self.fts.get_vector_alias_key(root, lang)
        search = build_pg_search(value, separator=self.fts.separator)
        query = {key: SearchQuery(value=search, config=lang.name, search_type="raw")}
        return Q(**query)


class SearchLanguage(UserString):
    """Postgres search language with the corresponding language code."""

    def __init__(self, name: FTSLang, *, code: LangCode) -> None:
        self.name = name
        self.code = code
        super().__init__(name)


class TextSearchLang:
    """Default postgres text search language configurations."""

    ARABIC = SearchLanguage("arabic", code="ar")
    ARMENIAN = SearchLanguage("armenian", code="hy")
    BASQUE = SearchLanguage("basque", code="eu")
    CATALAN = SearchLanguage("catalan", code="ca")
    DANISH = SearchLanguage("danish", code="da")
    DUTCH = SearchLanguage("dutch", code="nl")
    ENGLISH = SearchLanguage("english", code="en")
    FINNISH = SearchLanguage("finnish", code="fi")
    FRENCH = SearchLanguage("french", code="fr")
    GERMAN = SearchLanguage("german", code="de")
    GREEK = SearchLanguage("greek", code="el")
    HINDI = SearchLanguage("hindi", code="hi")
    HUNGARIAN = SearchLanguage("hungarian", code="hu")
    INDONESIAN = SearchLanguage("indonesian", code="id")
    IRISH = SearchLanguage("irish", code="ga")
    ITALIAN = SearchLanguage("italian", code="it")
    LITHUANIAN = SearchLanguage("lithuanian", code="lt")
    NEPALI = SearchLanguage("nepali", code="ne")
    NORWEGIAN = SearchLanguage("norwegian", code="nb")
    PORTUGUESE = SearchLanguage("portuguese", code="pt")
    ROMANIAN = SearchLanguage("romanian", code="ro")
    RUSSIAN = SearchLanguage("russian", code="ru")
    SERBIAN = SearchLanguage("serbian", code="sr")
    SPANISH = SearchLanguage("spanish", code="es")
    SWEDISH = SearchLanguage("swedish", code="sv")
    TAMIL = SearchLanguage("tamil", code="ta")
    TURKISH = SearchLanguage("turkish", code="tr")
    YIDDISH = SearchLanguage("yiddish", code="yi")

    @classmethod
    def members(cls) -> dict[str, SearchLanguage]:
        return get_members(cls, SearchLanguage)

    @classmethod
    def for_code(cls, code: LangCode, *, default: SearchLanguage = ENGLISH) -> SearchLanguage:
        members = cls.members()
        for search_lang in members.values():
            if search_lang.code == code:
                return search_lang
        return default


def normalize_search_text(text: str) -> str:
    """
    Normalize the given text to use in full text search.

    Replaces all non-word and non-space characters with spaces and removes multiple spaces.
    Each string of chars separated by space then becomes a search term.
    Each search term is then quoted and matched as a possible start of word.
    """
    text = unicodedata.normalize("NFKC", text)  # Normalize text to unicode form
    text = re.sub(r"[^\w\s]", " ", text)  # Remove all non-word and non-space characters
    return re.sub(r"\s+", " ", text)  # Collapse multiple spaces


def build_pg_search(text: str, *, separator: LangSep = "|") -> str:
    """
    Build raw postgres full text search query from the given text.
    Text is normalized first by removing punctuation, etc.

    Each search term is matched together with other search terms using the given operator.
      | = Only one of the search terms needs to match
      & = All search terms need to match
      <-> = Each search term must be followed by the others
      <3> = Each search term must be followed by less than 3 "words" away (<1> same as <->)

    Ref. https://www.postgresql.org/docs/current/datatype-textsearch.html#DATATYPE-TSQUERY
    """
    norm_text = normalize_search_text(text)
    search_terms = (f"'{value}':*" for value in norm_text.split(" ") if value)
    return f" {separator} ".join(search_terms)


def get_request_search_language(info: GQLInfo) -> SearchLanguage:
    """
    Get language from the given request using this order:

    1. Referer header path
    2. Request info path
    3. Cookie as set by the LANGUAGE_COOKIE_NAME setting
    4. Accept-Language header
    5. Default language as set by the LANGUAGE_CODE setting
    """
    referer = info.context.META.get("HTTP_REFERER")
    if referer:
        path = urllib.parse.urlparse(referer).path
        lang: LangCode = get_language_from_path(path)  # type: ignore[assignment]
        if lang is not None:
            return TextSearchLang.for_code(lang)

    lang = get_language_from_request(info.context, check_path=True)  # type: ignore[assignment,arg-type]
    return TextSearchLang.for_code(lang)
