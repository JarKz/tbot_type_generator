from functools import reduce
from typing import cast

from generators.imports import Imports


def map_type(original_types: list[str], required: bool) -> tuple[str, set[str]]:
    ARRAY_OF_LITERAL = "Array of "
    return_value = {
        True: {
            "True": "boolean",
            "Float number": "float",
            "Integer": "int",
            "Boolean": "boolean",
            "Float": "float"
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

    if len(original_types) == 1:
        original_type = original_types[0]

        if original_type in return_value[required]:
            return (return_value[required][original_type], set())
        if original_type.startswith(ARRAY_OF_LITERAL):
            return map_array_type(original_type)

        return (original_type, set())

    if original_types == ["Integer", "String"]:
        return ("String", set())
    if original_types == ["InputFile", "String"]:
        return ("InputFile", set())

    raise Exception("Unknown type!")


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


def generate_description(phrases: list[str], ident_spaces: int) -> str:
    ident = " " * ident_spaces
    description = f"{ident}/**\n"
    last = len(phrases) - 1
    for i, phrase in enumerate(phrases):
        description += f"{ident}* {phrase}\n"
        if i != last:
            description += f"{ident}*\n"
    description += "*/\n"
    return description


class Field:
    name: str
    camel_cased_name: str
    type_: str
    required: bool
    description: str
    annotations: set[str]
    imports: set[str]

    def parse(self, field: dict):
        self.name = field["name"]
        self.description = field["description"]
        self.camel_cased_name = to_camel_case(self.name)
        self.annotations = set()
        self.imports = set()

        if self.camel_cased_name != self.name:
            self.annotations.add(f"@SerializedName(\"{self.name}\")")
            self.imports.add(Imports.SerializedName.value)

        self.required = field["required"]
        if self.required:
            self.annotations.add("@NotNull")
            self.imports.add(Imports.NotNull.value)

        self.type_, imports = map_type(field["types"], self.required)
        self.imports = self.imports.union(imports)

    def to_text(self, ident_spaces: int) -> list[str]:
        ident = " " * ident_spaces
        lines = [
            f"{ident}/** {self.description} */\n"
        ]

        for annotation in self.annotations:
            lines.append(f"{ident}{annotation}\n")

        lines.append(f"{ident}public {self.type_} {self.camel_cased_name};\n")

        return lines


class TypeGenerator:
    name: str
    description: list[str]
    fields: list[Field]
    is_subtype: bool
    subtype_of: None | str
    subtypes: None | list[str]

    def __init__(self, telegram_type: dict):
        self.parse(telegram_type)

    def parse(self, telegram_type: dict):
        self.name = telegram_type["name"]
        self.description = telegram_type["description"]

        self.subtypes = telegram_type.get("subtypes")
        if self.subtypes is None:

            self.is_subtype = True

            self.subtype_of = telegram_type.get("subtype_of")
            if self.subtype_of is not None:
                if len(self.subtype_of) > 1:
                    raise Exception(
                        "Expected one subtype_of, but given many subtype_of!")
                self.subtype_of = self.subtype_of[0]
        else:
            self.is_subtype = False

        fields = []
        for field in telegram_type.get("fields", []):
            new_field = Field()
            new_field.parse(field)
            fields.append(new_field)

        self.fields = fields

    def make_method_equals(self, ident_spaces: int) -> tuple[list[str], str | None]:
        ident = " " * ident_spaces
        lines = [
            f"{ident}@Override\n",
            f"{ident}public final boolean equals(Object obj) {{\n"
            f"{ident * 2}if (this == obj) return true;\n"
            f"{ident * 2}if (!(obj instanceof {self.name} other)) return false;\n"
        ]

        if not self.fields:
            lines.append(f"{ident * 2}return true;\n")
            lines.append(f"{ident}}}\n")
            return (lines, None)

        exists_objects = False
        last = len(self.fields) - 1
        for i, field in enumerate(self.fields):
            line = ""
            if is_primitive(field.type_):
                line = f"{field.camel_cased_name} == other.{field.camel_cased_name}"
            else:
                line = f"Objects.equals({field.camel_cased_name}, other.{field.camel_cased_name})"
                exists_objects = True

            if i == 0:
                line = f"{ident * 2}return {line}"
            else:
                line = f"{ident * 4}&& {line}"

            if i == last:
                line += ";\n"
            else:
                line += "\n"

            lines.append(line)

        lines.append(f"{ident}}}\n")

        return (lines, Imports.Objects.value if exists_objects else None)

    def make_method_hash_code(self, ident_spaces: int) -> tuple[list[str], str | None]:
        ident = " " * ident_spaces
        lines = [
            f"{ident}@Override\n",
            f"{ident}public final int hashCode() {{\n"
        ]

        if not self.fields:
            lines.extend([
                f"{ident * 2}int prime = 31;\n",
                f"{ident * 2}return prime;\n",
                f"{ident}}}\n",
            ])
            return (lines, None)

        fields = ", ".join(
            map(lambda field: field.camel_cased_name, self.fields))
        lines.append(f"{ident * 2} return Objects.hash({fields});\n")
        lines.append(f"{ident}}}\n")

        return (lines, Imports.Objects.value)

    def make_method_to_string(self, ident_spaces: int) -> list[str]:
        ident = " " * ident_spaces
        lines = [
            f"{ident}@Override\n",
            f"{ident}public final String toString() {{\n"
        ]

        if not self.fields:
            lines.extend([
                f"{ident * 2}return \"{self.name}[]\";\n",
                f"{ident}}}\n",
            ])
            return lines

        lines.extend([
            f"{ident * 2}var builder = new StringBuilder();\n",
            f"{ident * 2}builder\n"
        ])
        name = f"{self.name}["

        for i, field in enumerate(self.fields):
            if i == 0:
                name += f"{field.camel_cased_name}="
            else:
                name = f", {field.camel_cased_name}="
            lines.append(f"{ident * 4}.append(\"{name}\")\n")
            lines.append(f"{ident * 4}.append({field.camel_cased_name})\n")

        lines.extend([
            f"{ident * 4}.append(\"]\");\n",
            f"{ident * 2}return builder.toString();\n",
            f"{ident}}}\n",
        ])

        return lines

    def to_text(self, package_name: str) -> list[str]:
        lines = [
            f"package {package_name}.{self.name};\n"
        ]
        empty_line = "\n"

        ident_spaces = 2

        used_imports = set()
        equals_method, import_objects = self.make_method_equals(ident_spaces)
        if import_objects is not None:
            used_imports.add(import_objects)

        hash_code_method, import_objects = self.make_method_hash_code(
            ident_spaces)
        if import_objects is not None:
            used_imports.add(import_objects)

        to_string_method = self.make_method_to_string(
            ident_spaces)

        all_imports = map(lambda field: field.imports, self.fields)
        used_imports = reduce(
            lambda left, right: left.union(right), all_imports, used_imports)
        if len(used_imports) > 0:
            lines.append(empty_line)
            for used_import in used_imports:
                lines.append(used_import + "\n")

        for _ in range(2):
            lines.append(empty_line)

        lines.append(generate_description(self.description, ident_spaces=0))

        if not self.is_subtype:
            subtypes = ", ".join(cast(list[str], self.subtypes))
            lines.append(
                f"sealed public interface {self.name} permits {subtypes} {{}}")
            return lines

        classname = f"public final class {self.name}"
        if self.subtype_of is not None:
            classname += f" implements {self.subtype_of}"

        classname += " {\n"
        lines.append(classname)
        lines.append(empty_line)

        last = len(self.fields) - 1
        for i, field in enumerate(self.fields):
            lines.extend(field.to_text(ident_spaces))
            if i != last:
                lines.append(empty_line)

        lines.append(empty_line)
        lines.extend(equals_method)
        lines.append(empty_line)
        lines.extend(hash_code_method)
        lines.append(empty_line)
        lines.extend(to_string_method)

        lines.append("}")

        return lines
