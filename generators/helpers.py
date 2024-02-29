from .imports import Imports


def map_type(original_types: list[str], required: bool, field_description: str = "") -> tuple[str, set[str]]:
    ARRAY_OF_LITERAL = "Array of "
    return_value = {
        True: {
            "True": "boolean",
            "Float number": "float",
            "Integer": "int",
            "Boolean": "boolean",
            "Float": "float",
            "Long": "long",
        },
        False: {
            "True": "Boolean",
            "Float number": "Float",
        }
    }

    def map_array_type(original_type: str) -> tuple[str, set[str]]:
        level = 0
        while original_type.startswith(ARRAY_OF_LITERAL):
            level += 1
            original_type = original_type[len(ARRAY_OF_LITERAL):]

        original_type = return_value[False][original_type] if original_type in return_value[False] else original_type
        for _ in range(level):
            original_type = f"List<{original_type}>"

        return (original_type, {Imports.List.value})

    def handle_type_by_description(original_type: str, description: str) -> str:
        if "attach://" in description and original_type == "String":
            original_type = "InputFile"

        if "64 bit" in field_description or "64-bit" in description and original_type == "Integer":
            original_type = "Long"

        return original_type

    if len(original_types) == 1:
        original_type = original_types[0]
        original_type = handle_type_by_description(original_type, field_description)

        if original_type in return_value[required]:
            return (return_value[required][original_type], set())
        if original_type.startswith(ARRAY_OF_LITERAL):
            return map_array_type(original_type)

        return (original_type, set())

    if original_types == ["Integer", "String"]:
        return ("Id", set())
    if original_types == ["InputFile", "String"]:
        return ("InputFile", set())

    raise Exception(f"Unknown type: {original_types}!")


def unwrap_type(original_type: str) -> str:
    LIST = "List<"

    while original_type.startswith(LIST):
        original_type = original_type[len(LIST):-1]

    return original_type


def is_primitive(type_name: str) -> bool:
    return type_name in ["int", "float", "long", "double", "char", "byte", "boolean", "short"]


def to_camel_case(field_name: str) -> str:
    words = field_name.split("_")
    if len(words) == 1:
        return field_name

    new_name = words[0]
    for word in words[1:]:
        new_name += word[0].upper() + word[1:]
    return new_name


def to_pascal_case(field_name: str) -> str:
    words = field_name.split("_")
    return "".join(map(lambda word: word[0].upper() + word[1:], words))


def generate_description(phrases: list[str], indent_spaces: int) -> str:
    indent = " " * indent_spaces
    description = f"{indent}/**\n"
    last = len(phrases) - 1
    for i, phrase in enumerate(phrases):
        description += f"{indent}* {phrase}\n"
        if i != last:
            description += f"{indent}*\n"
    description += "*/\n"
    return description
