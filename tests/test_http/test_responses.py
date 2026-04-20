from __future__ import annotations

from undine.http.responses import (
    HttpEventSourcingNotAllowedResponse,
    HttpMethodNotAllowedResponse,
    HttpUnsupportedContentTypeResponse,
)


def test_http_method_not_allowed_response() -> None:
    response = HttpMethodNotAllowedResponse(["GET", "POST"])

    assert response.status_code == 405
    assert response["Allow"] == "GET, POST"
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert response.content.decode() == "Method not allowed"


def test_http_unsupported_content_type_response() -> None:
    response = HttpUnsupportedContentTypeResponse(["text/html", "application/json"])

    assert response.status_code == 406
    assert response["Accept"] == "text/html, application/json"
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert response.content.decode() == "Server does not support any of the requested content types."


def test_http_event_sourcing_not_allowed_response() -> None:
    response = HttpEventSourcingNotAllowedResponse()

    assert response.status_code == 426
    assert response["Upgrade"] == "HTTP/2.0"
    assert response["Connection"] == "Upgrade"
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert response.content.decode() == "Cannot use Server-Sent Events with HTTP protocol lower than 2.0."
