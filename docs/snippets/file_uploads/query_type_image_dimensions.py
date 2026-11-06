from undine import Field, QueryType

from .models_image_dimensions import Task


class TaskType(QueryType[Task]):
    image = Field()
    image_width = Field()
    image_height = Field()
