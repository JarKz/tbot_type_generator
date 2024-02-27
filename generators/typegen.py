from functools import reduce
from typing import cast
from copy import copy
from enum import Enum

from .helpers import *


SPECIFIC_TYPES: dict[frozenset[str], str] = {}
ADDITIONAL_TYPES = []


class TypeClassification(Enum):
    DataType = 0
    MethodParameters = 1


class Field:
    name: str
    camel_cased_name: str
    type_: str
    required: bool
    description: str
    annotations: list[str]
    imports: set[str]

    def __init__(self, field: dict) -> None:
        self.parse(field)

    def parse(self, field: dict):
        self.name = field["name"]
        self.description = field["description"]
        self.camel_cased_name = to_camel_case(self.name)
        self.annotations = []
        self.imports = set()

        self.required = field["required"]
        if self.required:
            self.annotations.append("@NotNull")
            self.imports.add(Imports.NotNull.value)

        if self.camel_cased_name != self.name:
            self.annotations.append(f"@SerializedName(\"{self.name}\")")
            self.imports.add(Imports.SerializedName.value)

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

    DEFAULT_TYPE_CLASSIFICATION = TypeClassification.DataType
    type_classification: TypeClassification

    def __init__(self, telegram_type: dict, type_classification: None | TypeClassification = None):
        if type_classification is None:
            self.parse(telegram_type, self.DEFAULT_TYPE_CLASSIFICATION)
        else:
            self.parse(telegram_type, type_classification)

    def __parse_fields(self, raw_fields: list[dict]):
        fields = []
        match self.type_classification:
            case TypeClassification.DataType:
                fields = list(
                    map(lambda raw_field: Field(raw_field), raw_fields))
            case TypeClassification.MethodParameters:
                for raw_field in raw_fields:
                    types = frozenset(raw_field["types"])
                    if types in SPECIFIC_TYPES:
                        raw_field["types"] = [SPECIFIC_TYPES[types]]
                    elif len(types) > 2:
                        name = to_pascal_case(raw_field["name"])
                        new_type = name
                        data = {
                            "name": name,
                            "description": "",
                            "subtypes": list(types),
                        }
                        if all(map(lambda typename: typename.startswith("Array of"), types)):
                            new_type = "Array of " + name
                            data["subtypes"] = list(
                                map(lambda type_: type_[len("Array of "):], types))

                        ADDITIONAL_TYPES.append(TypeGenerator(data))
                        SPECIFIC_TYPES[types] = name

                        raw_field["types"] = [new_type]

                    fields.append(Field(raw_field))

        self.fields = fields

    def parse(self, telegram_type: dict, type_classification: TypeClassification):
        self.type_classification = type_classification

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

        self.__parse_fields(telegram_type.get("fields", []))

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
                if field.type_ == "float":
                    line = f"Float.floatToIntBits({field.camel_cased_name}) == Float.floatToIntBits(other.{field.camel_cased_name})"
                else:
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
            f"package {package_name};\n"
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

    @staticmethod
    def ensure_additional_types() -> list:
        to_return = copy(ADDITIONAL_TYPES)
        ADDITIONAL_TYPES.clear()
        return to_return
