from django.conf import settings
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=255)


class Task(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
