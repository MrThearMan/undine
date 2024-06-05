from django.db import models


class Task(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


class Step(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
