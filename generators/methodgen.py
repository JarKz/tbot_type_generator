
from generators.typegen import TypeGenerator


BOT_API_CLASS = [

]


class MethodGenerator:
    name: str
    parameter_name: str
    return_type: str

    def __init__(self) -> None:
        pass

    def create_body(self) -> list[str]:
        ...


class MethodGenerators:
    typegens: list[TypeGenerator]

    def __init__(self, typegens: list[TypeGenerator]) -> None:
        self.typegens = typegens

