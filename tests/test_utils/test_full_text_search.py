from __future__ import annotations

import pytest
from django.http import HttpRequest

from undine.typing import DjangoRequestProtocol
from undine.utils.full_text_search import (
    SearchLanguage,
    TextSearchLang,
    build_pg_search,
    get_request_search_language,
    normalize_search_text,
)


def test_text_search_lang__members() -> None:
    assert TextSearchLang.members() == {
        "ARABIC": SearchLanguage("arabic", code="ar"),
        "ARMENIAN": SearchLanguage("armenian", code="hy"),
        "BASQUE": SearchLanguage("basque", code="eu"),
        "CATALAN": SearchLanguage("catalan", code="ca"),
        "DANISH": SearchLanguage("danish", code="da"),
        "DUTCH": SearchLanguage("dutch", code="nl"),
        "ENGLISH": SearchLanguage("english", code="en"),
        "FINNISH": SearchLanguage("finnish", code="fi"),
        "FRENCH": SearchLanguage("french", code="fr"),
        "GERMAN": SearchLanguage("german", code="de"),
        "GREEK": SearchLanguage("greek", code="el"),
        "HINDI": SearchLanguage("hindi", code="hi"),
        "HUNGARIAN": SearchLanguage("hungarian", code="hu"),
        "INDONESIAN": SearchLanguage("indonesian", code="id"),
        "IRISH": SearchLanguage("irish", code="ga"),
        "ITALIAN": SearchLanguage("italian", code="it"),
        "LITHUANIAN": SearchLanguage("lithuanian", code="lt"),
        "NEPALI": SearchLanguage("nepali", code="ne"),
        "NORWEGIAN": SearchLanguage("norwegian", code="nb"),
        "PORTUGUESE": SearchLanguage("portuguese", code="pt"),
        "ROMANIAN": SearchLanguage("romanian", code="ro"),
        "RUSSIAN": SearchLanguage("russian", code="ru"),
        "SERBIAN": SearchLanguage("serbian", code="sr"),
        "SPANISH": SearchLanguage("spanish", code="es"),
        "SWEDISH": SearchLanguage("swedish", code="sv"),
        "TAMIL": SearchLanguage("tamil", code="ta"),
        "TURKISH": SearchLanguage("turkish", code="tr"),
        "YIDDISH": SearchLanguage("yiddish", code="yi"),
    }


def test_text_search_lang__for_code() -> None:
    en = SearchLanguage("english", code="en")
    fi = SearchLanguage("finnish", code="fi")

    assert TextSearchLang.for_code("en") == en
    assert TextSearchLang.for_code("en", default=fi) == en
    assert TextSearchLang.for_code("xx", default=fi) == fi


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("foo bar", "foo bar"),
        # Single space
        (" foo bar", " foo bar"),
        ("foo bar ", "foo bar "),
        (" foo bar ", " foo bar "),
        # Multiple spaces
        ("  foo bar", " foo bar"),
        ("foo bar  ", "foo bar "),
        ("  foo bar  ", " foo bar "),
        # Tabs
        ("\tfoo bar", " foo bar"),
        ("foo bar\t", "foo bar "),
        ("\tfoo bar\t", " foo bar "),
        # Multiple tabs
        ("\t\tfoo bar", " foo bar"),
        ("foo bar\t\t", "foo bar "),
        ("\t\tfoo bar\t\t", " foo bar "),
        # Non-word characters
        ("foo bar!", "foo bar "),
        ("foo bar?", "foo bar "),
        ("foo bar.", "foo bar "),
        ("foo bar,", "foo bar "),
        ("foo bar:", "foo bar "),
        ("foo bar's", "foo bar s"),
        ("(foo bar)", " foo bar "),
        # Normalize unicode
        ("\u00c5\u00e4\u00d6\u00f6", "ÅäÖö"),
    ],
)
def test_normalize_search_text(text, expected) -> None:
    assert normalize_search_text(text) == expected


@pytest.mark.parametrize(
    ("text", "separator", "expected"),
    [
        ("foo bar", "|", "'foo':* | 'bar':*"),
        ("foo bar", "&", "'foo':* & 'bar':*"),
        ("foo bar", "<->", "'foo':* <-> 'bar':*"),
        ("foo bar", "<3>", "'foo':* <3> 'bar':*"),
        ("foo bar baz", "|", "'foo':* | 'bar':* | 'baz':*"),
    ],
)
def test_build_pg_search(text, separator, expected):
    assert build_pg_search(text, separator=separator) == expected


def test_get_request_search_language__language_code(settings) -> None:
    request: DjangoRequestProtocol = HttpRequest()  # type: ignore[assignment]
    settings.LANGUAGE_CODE = "fi"

    assert get_request_search_language(request) == SearchLanguage("finnish", code="fi")


def test_get_request_search_language__accept_language(settings) -> None:
    request: DjangoRequestProtocol = HttpRequest()  # type: ignore[assignment]
    request.META["HTTP_ACCEPT_LANGUAGE"] = "fi"
    settings.LANGUAGE_CODE = "en"

    assert get_request_search_language(request) == SearchLanguage("finnish", code="fi")


def test_get_request_search_language__language_cookie(settings) -> None:
    request: DjangoRequestProtocol = HttpRequest()  # type: ignore[assignment]
    request.COOKIES[settings.LANGUAGE_COOKIE_NAME] = "fi"
    settings.LANGUAGE_CODE = "en"

    assert get_request_search_language(request) == SearchLanguage("finnish", code="fi")


def test_get_request_search_language__path_info(settings) -> None:
    request: DjangoRequestProtocol = HttpRequest()  # type: ignore[assignment]
    request.path_info = "/fi/"  # type: ignore[misc]
    settings.LANGUAGE_CODE = "en"

    assert get_request_search_language(request) == SearchLanguage("finnish", code="fi")


def test_get_request_search_language__referer_path(settings) -> None:
    request: DjangoRequestProtocol = HttpRequest()  # type: ignore[assignment]
    request.META["HTTP_REFERER"] = "https://example.com/fi/"
    settings.LANGUAGE_CODE = "en"

    assert get_request_search_language(request) == SearchLanguage("finnish", code="fi")


def test_get_request_search_language__referer_path__no_lang(settings) -> None:
    request: DjangoRequestProtocol = HttpRequest()  # type: ignore[assignment]
    request.META["HTTP_REFERER"] = "https://example.com/"
    settings.LANGUAGE_CODE = "en"

    assert get_request_search_language(request) == SearchLanguage("english", code="en")
