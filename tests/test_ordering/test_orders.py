from django.db.models import CASCADE, CharField, DateTimeField, ForeignKey, ImageField, Model

from undine.ordering import get_orders_for_model


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

    image = ImageField(null=True, blank=True)

    relation = ForeignKey(Relation, on_delete=CASCADE, related_name="examples")

    class Meta:
        managed = False
        app_label = __name__

    def __str__(self) -> str:
        return self.name


def test_get_orders_for_model():
    fields = get_orders_for_model(Example, exclude=[])
    assert sorted(fields) == ["created_at", "name", "pk"]


def test_get_orders_for_model__exclude():
    fields = get_orders_for_model(Example, exclude=["name"])
    assert sorted(fields) == ["created_at", "pk"]
