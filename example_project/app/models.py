from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import (
    CASCADE,
    RESTRICT,
    SET_NULL,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    DurationField,
    EmailField,
    FileField,
    ForeignKey,
    ImageField,
    IntegerField,
    JSONField,
    ManyToManyField,
    Model,
    OneToOneField,
    TextChoices,
    TextField,
    TimeField,
    URLField,
    UUIDField,
)

if TYPE_CHECKING:
    from undine.typing import RelatedManager

__all__ = [
    "AcceptanceCriteria",
    "Comment",
    "Person",
    "Project",
    "Report",
    "ServiceRequest",
    "Task",
    "TaskObjective",
    "TaskResult",
    "TaskStep",
    "TaskTypeChoices",
    "Team",
]


class TaskTypeChoices(TextChoices):
    """Task type choices."""

    BUG_FIX = "BUG_FIX", "Bug Fix"
    TASK = "TASK", "Task"
    STORY = "STORY", "Story"


class Person(Model):
    name = CharField(max_length=255)
    email = EmailField(unique=True)

    def __str__(self) -> str:
        return f"Person {self.name}"


class Comment(Model):
    contents = TextField()
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    commenter = ForeignKey(Person, on_delete=CASCADE, related_name="comments")

    object_id = CharField(max_length=255)
    content_type = ForeignKey(ContentType, on_delete=CASCADE)
    target = GenericForeignKey()

    def __str__(self) -> str:
        return f"Comment {self.id}"


class ServiceRequest(Model):
    details = TextField()
    created_at = DateField(auto_now_add=True)
    submitted_at = DateField(null=True, blank=True)

    def __str__(self) -> str:
        return f"ServiceRequest {self.id}"


class Team(Model):
    name = CharField(max_length=255)

    members = ManyToManyField(Person, related_name="teams")

    def __str__(self) -> str:
        return f"Team {self.name}"


class Project(Model):
    name = CharField(max_length=255)

    team = ForeignKey(Team, on_delete=CASCADE, related_name="projects")

    comments = GenericRelation(Comment)

    def __str__(self) -> str:
        return f"Project {self.name}"


class Task(Model):
    name = CharField(max_length=255)
    type = CharField(choices=TaskTypeChoices.choices, max_length=255)
    created_at = DateTimeField(auto_now_add=True)
    done = BooleanField(default=False)
    due_by = DateField(null=True, blank=True)
    check_time = TimeField(null=True, blank=True)
    points = IntegerField(null=True, blank=True)
    progress = DecimalField(default=0, max_digits=3, decimal_places=2)
    worked_hours = DurationField(default=datetime.timedelta)
    contact_email = EmailField(null=True, blank=True)  # noqa: DJ001
    demo_url = URLField(null=True, blank=True)  # noqa: DJ001
    external_uuid = UUIDField(null=True, blank=True)
    extra_data = JSONField(null=True, blank=True)
    image = ImageField(null=True, blank=True)
    attachment = FileField(null=True, blank=True)

    related_tasks: RelatedManager[Task] = ManyToManyField("self")

    request = OneToOneField(ServiceRequest, null=True, blank=True, default=None, on_delete=SET_NULL)
    project = ForeignKey(Project, null=True, blank=True, on_delete=CASCADE, related_name="tasks")
    assignees: RelatedManager[Person] = ManyToManyField(Person, related_name="tasks")

    comments: RelatedManager[Comment] = GenericRelation(Comment)

    # Reverse relation hints
    result: TaskResult | None
    objective: TaskObjective | None
    steps: RelatedManager[TaskStep]
    acceptancecriteria: RelatedManager[AcceptanceCriteria]
    reports: RelatedManager[Report]

    def __str__(self) -> str:
        return f"Task {self.name}"


class TaskResult(Model):
    details = TextField()
    time_used = DurationField()
    created_at = DateField(auto_now_add=True)

    task = OneToOneField(Task, on_delete=RESTRICT, related_name="result")

    def __str__(self) -> str:
        return f"TaskResult {self.id}"


class TaskObjective(Model):
    details = TextField()

    task = OneToOneField(Task, null=True, blank=True, on_delete=CASCADE, related_name="objective")

    def __str__(self) -> str:
        return f"TaskObjective {self.id}"


class TaskStep(Model):
    name = CharField(max_length=255)
    done = BooleanField(default=False)

    task = ForeignKey(Task, on_delete=CASCADE, related_name="steps")

    def __str__(self) -> str:
        return f"TaskStep {self.id}"


class AcceptanceCriteria(Model):
    details = TextField()
    fulfilled = BooleanField(default=False)

    task = ForeignKey(Task, on_delete=CASCADE)  # No related_name on purpose.

    def __str__(self) -> str:
        return f"AcceptanceCriteria {self.id}"


class Report(Model):
    name = CharField(max_length=255)
    content = TextField()
    created_at = DateField(auto_now_add=True)

    tasks = ManyToManyField(Task, related_name="reports")

    def __str__(self) -> str:
        return f"Report {self.name}"
