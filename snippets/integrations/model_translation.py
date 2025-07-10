from django.db import models
from modeltranslation.decorators import register
from modeltranslation.translator import TranslationOptions

# In settings.py:
#
# MODELTRANSLATION_LANGUAGES = ("en", "fi")


class Task(models.Model):
    name = models.CharField(max_length=255)

    # From modeltranslation
    name_en: str | None
    name_fi: str | None


@register(Task)
class TaskTranslationOptions(TranslationOptions):
    fields = ["name"]
