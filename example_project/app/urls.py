from __future__ import annotations

from django.urls import path

from example_project.app import views

urlpatterns = [
    path("websocket-testing/", views.websocket_testing, name="websocket_testing"),
    path("sse-testing/", views.sse_testing, name="sse_testing"),
    path("sse-testing/dc/", views.sse_testing_dc, name="sse_testing_dc"),
    path("sse-testing/sc/", views.sse_testing_sc, name="sse_testing_sc"),
]
