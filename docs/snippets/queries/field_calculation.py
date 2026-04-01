from django.db.models import Value

from undine import Calculation, CalculationArgument, Field, GQLInfo, QueryType
from undine.typing import DjangoExpression

from .models import Task


class ExampleCalculation(Calculation[int]):
    value = CalculationArgument(int)

    def __call__(self, info: GQLInfo) -> DjangoExpression:
        # Some impressive calculation here
        return Value(self.value)


class TaskType(QueryType[Task]):
    calc = Field(ExampleCalculation)
