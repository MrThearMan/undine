from typing import Any

from django.http import HttpRequest, HttpResponse

from undine.persisted_documents.views import PersistedDocumentsView


class RegisterPersistedDocumentsView(PersistedDocumentsView):
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Add permission checks here
        return super().dispatch(request, *args, **kwargs)
