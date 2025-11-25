from django.db import models


class Task(models.Model):
    name = models.CharField(max_length=255)

    # Created by modeltranslation
    name_en: str | None
    name_fi: str | None
