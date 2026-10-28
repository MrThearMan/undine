from undine import Input, MutationType

from .models import Membership, Project


class ProjectMembership(MutationType[Membership], kind="related"):
    pk = Input()
    person = Input()
    role = Input()


class ProjectUpdateMutation(MutationType[Project], related_action="delete"):
    pk = Input()
    name = Input()
    memberships = Input(ProjectMembership)
