from modeltranslation.decorators import register
from modeltranslation.translator import TranslationOptions

from .models import Task


@register(Task)
class TaskTranslationOptions(TranslationOptions):
    fields = ["name"]
