from django.db import models


class Task(models.Model):
    name = models.CharField(max_length=255)

    image = models.ImageField(width_field="image_width", height_field="image_height")
    image_width = models.PositiveIntegerField(editable=False)
    image_height = models.PositiveIntegerField(editable=False)
