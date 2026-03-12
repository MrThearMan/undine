from __future__ import annotations

from typing import NamedTuple

import pytest
from django.http.request import MediaType

from tests.helpers import parametrize_helper
from undine.http.content_negotiation import get_preferred_response_content_type


class Input(NamedTuple):
    accepted: list[str]
    supported: list[str]
    all_types_override: str | None
    expected: str


@pytest.mark.parametrize(
    **parametrize_helper({
        "Single accepted type": Input(
            accepted=["application/json"],
            supported=["application/json", "text/html"],
            all_types_override=None,
            expected="application/json",
        ),
        "Any type": Input(
            accepted=["*/*"],
            supported=["application/json", "text/html"],
            all_types_override=None,
            expected="application/json",
        ),
        "Not supported type": Input(
            accepted=["application/json"],
            supported=["text/html"],
            all_types_override=None,
            expected="None",
        ),
        "Any type with override": Input(
            accepted=["*/*"],
            supported=["application/json", "text/html"],
            all_types_override="text/html",
            expected="text/html",
        ),
        "No any type with override": Input(
            accepted=["application/json"],
            supported=["application/json", "text/html"],
            all_types_override="text/html",
            expected="application/json",
        ),
        "With override but has more specific accepted type": Input(
            accepted=["application/json", "*/*"],
            supported=["application/json", "text/html"],
            all_types_override="text/html",
            expected="application/json",
        ),
        "Two types select first supported one": Input(
            accepted=["text/html", "application/json"],
            supported=["application/json", "text/html"],
            all_types_override=None,
            expected="application/json",
        ),
        "Two types select one with higher quantity": Input(
            accepted=["application/json", "text/html;q=0.8"],
            supported=["text/html", "application/json"],
            all_types_override=None,
            expected="application/json",
        ),
        "Two types select one with higher specificity": Input(
            accepted=["application/json", "text/*"],
            supported=["text/html", "application/json"],
            all_types_override=None,
            expected="application/json",
        ),
        "Two types select one without parameters": Input(
            accepted=["application/json", "multipart/mixed"],
            supported=["multipart/mixed;subscriptionSpec=1.0", "multipart/mixed", "application/json"],
            all_types_override=None,
            expected="multipart/mixed",
        ),
        "Two types select one with matching parameters": Input(
            accepted=["multipart/mixed;subscriptionSpec=1.0"],
            supported=["multipart/mixed;subscriptionSpec=1.0", "multipart/mixed", "application/json"],
            all_types_override=None,
            expected="multipart/mixed; subscriptionspec=1.0",
        ),
    })
)
def test_get_preferred_response_content_type(accepted, supported, all_types_override, expected):
    content_type = get_preferred_response_content_type(
        accepted=[MediaType(at) for at in accepted],
        supported=supported,
        all_types_override=all_types_override,
    )
    assert str(content_type) == expected
