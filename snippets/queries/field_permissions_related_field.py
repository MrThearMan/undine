from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError

from .models import Project, Task


class ProjectType(QueryType[Project]):
    @classmethod
    def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
        # Not called if 'ProjectType' is accessed from 'TaskType.project'
        # because it has a permissions check already
        if not info.context.user.is_superuser:
            raise GraphQLPermissionError


class TaskType(QueryType[Task]):
    project = Field()

    @project.permissions
    def project_permissions(self, info: GQLInfo, value: Project) -> None:
        if not info.context.user.is_authenticated:
            raise GraphQLPermissionError
