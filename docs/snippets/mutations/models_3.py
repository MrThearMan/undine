from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=255)


class Project(models.Model):
    name = models.CharField(max_length=255)

    members = models.ManyToManyField(Person, through="Membership", related_name="projects")


class Membership(models.Model):
    role = models.CharField(max_length=255)

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="memberships")
