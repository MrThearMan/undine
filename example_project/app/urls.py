from __future__ import annotations

from django.urls import path

from example_project.app import views

urlpatterns = [
    path("websocket-testing/", views.websocket_testing, name="websocket_testing"),
]
