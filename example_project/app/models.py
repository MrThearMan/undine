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
    "TaskObjective",
    "TaskResult",
    "TaskStep",
    "TaskTypeChoices",
    "Team",
]


class TaskTypeChoices(models.TextChoices):
    """Task type choices."""

    BUG_FIX = "BUG_FIX", "Bug Fix"
    TASK = "TASK", "Task"
    STORY = "STORY", "Story"


class Person(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        return f"Person {self.name}"


class Comment(models.Model):
    contents = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    commenter = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="comments")

    object_id = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target = GenericForeignKey()

    def __str__(self) -> str:
        return f"Comment {self.id}"


class ServiceRequest(models.Model):
    details = models.TextField()
    created_at = models.DateField(auto_now_add=True)
    submitted_at = models.DateField(null=True, blank=True)

    def __str__(self) -> str:
        return f"ServiceRequest {self.id}"


class Team(models.Model):
    name = models.CharField(max_length=255)

    members = models.ManyToManyField(Person, related_name="teams")

    def __str__(self) -> str:
        return f"Team {self.name}"


class Project(models.Model):
    name = models.CharField(max_length=255)

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="projects")

    comments = GenericRelation(Comment)

    def __str__(self) -> str:
        return f"Project {self.name}"


class Task(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(choices=TaskTypeChoices.choices, max_length=255)
    created_at = models.DateField(auto_now_add=True)

    related_tasks = models.ManyToManyField("self")

    request = models.OneToOneField(ServiceRequest, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.CASCADE, related_name="tasks")
    assignees = models.ManyToManyField(Person, related_name="tasks")

    comments = GenericRelation(Comment)

    def __str__(self) -> str:
        return f"Task {self.name}"


class TaskResult(models.Model):
    details = models.TextField()
    time_used = models.DurationField()
    created_at = models.DateField(auto_now_add=True)

    task = models.OneToOneField(Task, on_delete=models.RESTRICT, related_name="result")

    def __str__(self) -> str:
        return f"TaskResult {self.id}"


class TaskObjective(models.Model):
    details = models.TextField()

    task = models.OneToOneField(Task, null=True, blank=True, on_delete=models.CASCADE, related_name="objective")

    def __str__(self) -> str:
        return f"TaskObjective {self.id}"


class TaskStep(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="steps")

    def __str__(self) -> str:
        return f"TaskStep {self.id}"


class AcceptanceCriteria(models.Model):
    details = models.TextField()
    fulfilled = models.BooleanField(default=False)

    task = models.ForeignKey(Task, on_delete=models.CASCADE)  # No related_name on purpose.

    def __str__(self) -> str:
        return f"AcceptanceCriteria {self.id}"


class Report(models.Model):
    name = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateField(auto_now_add=True)

    tasks = models.ManyToManyField(Task, related_name="reports")

    def __str__(self) -> str:
        return f"Report {self.name}"


# --------------------------------------------------------------------


class BaseModel(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["pk"]
        abstract = True

    def __str__(self) -> str:
        return self.__class__.__name__ + ": " + self.name


class Example(BaseModel):
    symmetrical_field = models.ManyToManyField("self")
    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOne",
        on_delete=models.CASCADE,
        related_name="example_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOne",
        on_delete=models.CASCADE,
        related_name="example_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToMany",
        related_name="example_rels",
    )

    named_relation = models.ForeignKey(
        "Task",
        on_delete=models.CASCADE,
        related_name="+",
    )


# --------------------------------------------------------------------


class ForwardOneToOne(BaseModel):
    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_one_to_one_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_one_to_one_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="forward_one_to_one_rels",
    )


class ForwardManyToOne(BaseModel):
    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_many_to_one_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_many_to_one_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="forward_many_to_one_rels",
    )


class ForwardManyToMany(BaseModel):
    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_many_to_many_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_many_to_many_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="forward_many_to_many_rels",
    )


class ReverseOneToOne(BaseModel):
    example_field = models.OneToOneField(
        "Example",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )

    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="reverse_one_to_one_rels",
    )


class ReverseOneToMany(BaseModel):
    example_field = models.ForeignKey(
        "Example",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )

    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="reverse_one_to_many_rels",
    )


class ReverseManyToMany(BaseModel):
    example_fields = models.ManyToManyField(
        "Example",
        related_name="reverse_many_to_many_rels",
    )

    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_many_to_many_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_many_to_many_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="reverse_many_to_many_rels",
    )


# --------------------------------------------------------------------


class ForwardOneToOneForRelated(BaseModel):
    pass


class ForwardManyToOneForRelated(BaseModel):
    pass


class ForwardManyToManyForRelated(BaseModel):
    pass


# --------------------------------------------------------------------


class ReverseOneToOneToForwardOneToOne(BaseModel):
    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToForwardManyToOne(BaseModel):
    forward_many_to_one_field = models.OneToOneField(
        "ForwardManyToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToForwardManyToMany(BaseModel):
    forward_many_to_many_field = models.OneToOneField(
        "ForwardManyToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToReverseOneToOne(BaseModel):
    reverse_one_to_one_field = models.OneToOneField(
        "ReverseOneToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToReverseOneToMany(BaseModel):
    reverse_many_to_one_field = models.OneToOneField(
        "ReverseOneToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToReverseManyToMany(BaseModel):
    reverse_many_to_many_field = models.OneToOneField(
        "ReverseManyToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


# --------------------------------------------------------------------


class ReverseOneToManyToForwardOneToOne(BaseModel):
    forward_one_to_one_field = models.ForeignKey(
        "ForwardOneToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToForwardManyToOne(BaseModel):
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToForwardManyToMany(BaseModel):
    forward_many_to_many_field = models.ForeignKey(
        "ForwardManyToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToReverseOneToOne(BaseModel):
    reverse_one_to_one_field = models.ForeignKey(
        "ReverseOneToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToReverseOneToMany(BaseModel):
    reverse_many_to_one_field = models.ForeignKey(
        "ReverseOneToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToReverseManyToMany(BaseModel):
    reverse_many_to_many_field = models.ForeignKey(
        "ReverseManyToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


# --------------------------------------------------------------------


class ReverseManyToManyToForwardOneToOne(BaseModel):
    forward_one_to_one_fields = models.ManyToManyField(
        "ForwardOneToOne",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToForwardManyToOne(BaseModel):
    forward_many_to_one_fields = models.ManyToManyField(
        "ForwardManyToOne",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToForwardManyToMany(BaseModel):
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToMany",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToReverseOneToOne(BaseModel):
    reverse_one_to_one_fields = models.ManyToManyField(
        "ReverseOneToOne",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToReverseOneToMany(BaseModel):
    reverse_many_to_one_fields = models.ManyToManyField(
        "ReverseOneToMany",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToReverseManyToMany(BaseModel):
    reverse_many_to_many_fields = models.ManyToManyField(
        "ReverseManyToMany",
        related_name="reverse_many_to_many_rels",
    )
