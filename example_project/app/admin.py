from django.contrib import admin

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
