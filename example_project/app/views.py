from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render
from django.urls import reverse

from undine.settings import undine_settings

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def websocket_testing(request: HttpRequest) -> HttpResponse:
    context = {
        "ws_path": undine_settings.WEBSOCKET_PATH,
    }
    return render(request, "app/websocket_testing.html", context=context)


def sse_testing(request: HttpRequest) -> HttpResponse:
    return HttpResponsePermanentRedirect(redirect_to=reverse("sse_testing_dc"))


def sse_testing_dc(request: HttpRequest) -> HttpResponse:
    return render(request, "app/sse_testing_dc.html")


def sse_testing_sc(request: HttpRequest) -> HttpResponse:
    return render(request, "app/sse_testing_sc.html")
