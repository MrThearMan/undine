from undine import RootType


class Query(RootType, extensions={"foo": "bar"}): ...
