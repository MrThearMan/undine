from __future__ import annotations

import json

from django.contrib import admin
from django.contrib.sessions.models import Session
from django.utils.safestring import mark_safe

from .models import (
    AcceptanceCriteria,
    Comment,
    Person,
    Project,
    Report,
    ServiceRequest,
    Task,
    TaskResult,
    TaskStep,
    Team,
)


@admin.register(AcceptanceCriteria)
class AcceptanceCriteriaAdmin(admin.ModelAdmin): ...


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin): ...


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin): ...


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin): ...


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin): ...


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin): ...


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin): ...


@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin): ...


@admin.register(TaskStep)
class TaskStepAdmin(admin.ModelAdmin): ...


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin): ...


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    fields = (
        "session_key",
        "session_data_decoded",
        "expire_date",
    )
    readonly_fields = (
        "session_key",
        "expire_date",
        "session_data_decoded",
    )

    @admin.display(description="Session data")
    def session_data_decoded(self, obj: Session) -> str:
        session_store = Session.get_session_store_class()
        session = session_store(obj.session_key)
        data = json.dumps(session.load(), indent=2, sort_keys=True)
        return mark_safe(f"<pre>{data}</pre>")  # noqa: S308
