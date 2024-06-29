from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

__all__ = [
    "AcceptanceCriteria",
    "Comment",
    "Person",
    "Project",
    "Report",
    "ServiceRequest",
    "Task",
    "TaskResult",
    "TaskStep",
    "TaskType",
    "Team",
]


class TaskType(models.TextChoices):
    BUG_FIX = "BUG_FIX"
    TASK = "TASK"
    STORY = "STORY"


class Person(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)


class Comment(models.Model):
    contents = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    commenter = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="comments")

    object_id = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target = GenericForeignKey()


class ServiceRequest(models.Model):
    details = models.TextField()
    created_at = models.DateField(auto_now_add=True)
    submitted_at = models.DateField(null=True)


class Team(models.Model):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(Person)


class Project(models.Model):
    name = models.CharField(max_length=255)

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="projects")

    comments = GenericRelation(Comment)


class Task(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(choices=TaskType.choices, max_length=255)
    created_at = models.DateField(auto_now_add=True)

    related_tasks = models.ManyToManyField("self")

    request = models.OneToOneField(ServiceRequest, null=True, default=None, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    assignees = models.ManyToManyField(Person, related_name="tasks")

    comments = GenericRelation(Comment)


class TaskResult(models.Model):
    details = models.TextField()
    time_used = models.DurationField()
    created_at = models.DateField(auto_now_add=True)

    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name="result")


class TaskStep(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="steps")


class AcceptanceCriteria(models.Model):
    details = models.TextField()
    fulfilled = models.BooleanField(default=False)

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="acceptance_criteria")


class Report(models.Model):
    name = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateField(auto_now_add=True)

    tasks = models.ManyToManyField(Task, related_name="reports")
