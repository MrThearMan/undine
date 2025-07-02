from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import render

from undine.settings import undine_settings

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def websocket_testing(request: HttpRequest) -> HttpResponse:
    context = {
        "ws_path": undine_settings.WEBSOCKET_PATH,
    }
    return render(request, "app/websocket_testing.html", context=context)
