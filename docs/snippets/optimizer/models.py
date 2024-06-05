from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=255)


class Task(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    project = models.ForeignKey(Project, on_delete=models.CASCADE)


class Step(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)

    task = models.ForeignKey(Task, on_delete=models.CASCADE)
