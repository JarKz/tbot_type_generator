
from generators.typegen import Type


BOT_API_CLASS = [

]


class Method:
    name: str
    parameter_name: str
    return_type: str

    def __init__(self) -> None:
        pass

    def create_body(self) -> list[str]:
        ...


class MethodGenerator:
    types: list[Type]

    def __init__(self, types: list[Type]) -> None:
        self.types = types

