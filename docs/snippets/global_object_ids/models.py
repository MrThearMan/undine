from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)


class Task(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    assignees = models.ManyToManyField(Person)
