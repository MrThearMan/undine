from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=255)


class Task(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # The User entity is owned by another subgraph, so we only store its key locally.
    assigned_to_id = models.IntegerField(null=True, blank=True)
