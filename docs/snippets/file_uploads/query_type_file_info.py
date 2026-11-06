from pathlib import Path
from typing import TypedDict

from undine import Field, GQLInfo, QueryType

from .models import Task


class FileInfo(TypedDict):
    url: str
    name: str


class TaskType(QueryType[Task]):
    attachment = Field(FileInfo, nullable=True)

    @attachment.resolve
    def resolve_attachment(root: Task, info: GQLInfo) -> FileInfo | None:
        if not root.attachment:
            return None
        return FileInfo(url=root.attachment.url, name=Path(root.attachment.name).name)
