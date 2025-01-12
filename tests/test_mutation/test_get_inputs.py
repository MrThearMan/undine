from django.db.models import CASCADE, CharField, DateTimeField, ForeignKey, Model

from undine.mutation import get_inputs_for_model


class Relation(Model):
    name = CharField(max_length=255)

    class Meta:
        managed = False
        app_label = __name__

    def __str__(self) -> str:
        return self.name


class Example(Model):
    name = CharField(max_length=255)
    created_at = DateTimeField(auto_now_add=True)

    relation = ForeignKey(Relation, on_delete=CASCADE, related_name="examples")

    class Meta:
        managed = False
        app_label = __name__

    def __str__(self) -> str:
        return self.name


def test_get_inputs_for_model():
    fields = get_inputs_for_model(Example, exclude=[])
    assert sorted(fields) == ["name", "pk", "relation"]


def test_get_inputs_for_model__exclude():
    fields = get_inputs_for_model(Example, exclude=["name"])
    assert sorted(fields) == ["pk", "relation"]
