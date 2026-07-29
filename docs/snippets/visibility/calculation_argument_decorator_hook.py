from django.db.models import Value

from undine import Calculation, CalculationArgument
from undine.typing import DjangoExpression, DjangoRequestProtocol, GQLInfo


class ExampleCalculation(Calculation[int]):
    value = CalculationArgument(int)

    def __call__(self, info: GQLInfo) -> DjangoExpression:
        return Value(self.value)

    @value.visible
    def value_visible(self, request: DjangoRequestProtocol) -> bool:
        return request.user.is_authenticated
