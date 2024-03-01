from functools import reduce
from typing import cast
from copy import copy
from enum import Enum
import re

from .helpers import *


class TypeClassification(Enum):
    DataType = "types"
    MethodParameters = "core.parameters"

    def package(self) -> str:
        return self.value


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
            self.imports.add(Imports.NotNull.as_line())

        if self.camel_cased_name != self.name:
            self.annotations.append(f"@SerializedName(\"{self.name}\")")
            self.imports.add(Imports.SerializedName.as_line())

        self.type_, imports = map_type(
            field["types"], self.required, self.description)
        self.imports = self.imports.union(imports)

    def to_java_code(self, indent_spaces: int, type_classification: TypeClassification) -> list[str]:
        def get_constant_if_matches() -> None | str:
            regexs = [re.compile("must be \\w*$"), re.compile("always \"\\w*\"$")]
            for regex in regexs:
                match = regex.findall(self.description)
                if match:
                    data: str = match[0].split(" ")[-1]
                    if not data.startswith('"'):
                        data = '"' + data + '"'
                    return f"{indent}public static final {self.type_} {self.name.upper()} = {data};\n"
            return None

        indent = " " * indent_spaces
        lines = [
            f"{indent}/** {self.description} */\n"
        ]

        is_constant = False
        if type_classification == TypeClassification.DataType:
            constant_line = get_constant_if_matches()
            if constant_line is not None:
                lines.insert(0, constant_line)
                is_constant = True

        for annotation in self.annotations:
            lines.append(f"{indent}{annotation}\n")

        field_line = f"{indent}public "
        if is_constant:
            field_line += f" final {self.type_} {self.camel_cased_name} = {self.name.upper()};\n"
        else:
            field_line += f"{self.type_} {self.camel_cased_name};\n"

        lines.append(field_line)

        return lines


class TypeGenerator:
    name: str
    description: list[str]
    fields: list[Field]
    is_subtype: bool
    subtype_of: None | list[str]
    subtypes: None | list[str]
    imports: set[str]

    DEFAULT_TYPE_CLASSIFICATION = TypeClassification.DataType
    type_classification: TypeClassification

    def __init__(self, telegram_type: dict, type_classification: None | TypeClassification = None):
        if type_classification is None:
            self.parse(telegram_type, self.DEFAULT_TYPE_CLASSIFICATION)
        else:
            self.parse(telegram_type, type_classification)

    def __create_new_interface(self, raw_field: dict) -> str:
        types: list[str] = raw_field["types"]
        name = to_pascal_case(raw_field["name"])

        new_type = name
        data = {
            "name": name,
            "description": "",
            "subtypes": types,
        }
        if all(map(lambda typename: typename.startswith("Array of"), types)):
            new_type = "Array of " + name
            data["subtypes"] = list(
                map(lambda type_: type_[len("Array of "):], types))

        ADDITIONAL_TYPES.append(TypeGenerator(
            data, TypeGenerator.DEFAULT_TYPE_CLASSIFICATION))
        SPECIFIC_TYPES[frozenset(types)] = name

        return new_type

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
                        new_type = self.__create_new_interface(raw_field)
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
                self.subtype_of = self.subtype_of
        else:
            self.is_subtype = False

        self.imports = set()
        self.__parse_fields(telegram_type.get("fields", []))

    def make_method_equals(self, indent_spaces: int) -> list[str]:
        indent = " " * indent_spaces
        lines = [
            f"{indent}@Override\n",
            f"{indent}public final boolean equals(Object obj) {{\n"
            f"{indent * 2}if (this == obj) return true;\n"
            f"{indent * 2}if (!(obj instanceof {self.name} other)) return false;\n"
        ]

        if not self.fields:
            lines.append(f"{indent * 2}return true;\n")
            lines.append(f"{indent}}}\n")
            return lines

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
                line = f"{indent * 2}return {line}"
            else:
                line = f"{indent * 4}&& {line}"

            if i == last:
                line += ";\n"
            else:
                line += "\n"

            lines.append(line)

        lines.append(f"{indent}}}\n")

        if exists_objects:
            self.imports.add(Imports.Objects.as_line())

        return lines

    def make_method_hash_code(self, indent_spaces: int) -> list[str]:
        indent = " " * indent_spaces
        lines = [
            f"{indent}@Override\n",
            f"{indent}public final int hashCode() {{\n"
        ]

        if not self.fields:
            lines.extend([
                f"{indent * 2}int prime = 31;\n",
                f"{indent * 2}return prime;\n",
                f"{indent}}}\n",
            ])
            return lines

        fields = ", ".join(
            map(lambda field: field.camel_cased_name, self.fields))
        lines.append(f"{indent * 2} return Objects.hash({fields});\n")
        lines.append(f"{indent}}}\n")

        self.imports.add(Imports.Objects.as_line())

        return lines

    def make_method_to_string(self, indent_spaces: int) -> list[str]:
        indent = " " * indent_spaces
        lines = [
            f"{indent}@Override\n",
            f"{indent}public final String toString() {{\n"
        ]

        if not self.fields:
            lines.extend([
                f"{indent * 2}return \"{self.name}[]\";\n",
                f"{indent}}}\n",
            ])
            return lines

        lines.extend([
            f"{indent * 2}var builder = new StringBuilder();\n",
            f"{indent * 2}builder\n"
        ])
        name = f"{self.name}["

        for i, field in enumerate(self.fields):
            if i == 0:
                name += f"{field.camel_cased_name}="
            else:
                name = f", {field.camel_cased_name}="
            lines.append(f"{indent * 4}.append(\"{name}\")\n")
            lines.append(f"{indent * 4}.append({field.camel_cased_name})\n")

        lines.extend([
            f"{indent * 4}.append(\"]\");\n",
            f"{indent * 2}return builder.toString();\n",
            f"{indent}}}\n",
        ])

        return lines

    def to_java_code(self, base_packagename: str) -> list[str]:
        lines = [
            f"package {base_packagename}.{self.type_classification.package()};\n"
        ]
        empty_line = "\n"

        indent_spaces = 2

        equals_method = self.make_method_equals(indent_spaces)
        hash_code_method = self.make_method_hash_code(indent_spaces)
        to_string_method = self.make_method_to_string(indent_spaces)

        all_imports = map(lambda field: field.imports, self.fields)
        self.imports = reduce(lambda lhs, rhs: lhs.union(
            rhs), all_imports, self.imports)

        if len(self.imports) > 0:
            lines.append(empty_line)
            for used_import in self.imports:
                lines.append(used_import + "\n")

        for _ in range(2):
            lines.append(empty_line)

        lines.append(generate_description(self.description, indent_spaces=0))

        if not self.is_subtype:
            subtypes = ", ".join(cast(list[str], self.subtypes))
            lines.append(
                f"sealed public interface {self.name} permits {subtypes} {{}}")
            return lines

        classname = f"public final class {self.name}"
        if self.subtype_of is not None:
            supertypes = ", ".join(self.subtype_of)
            classname += f" implements {supertypes}"

        classname += " {\n"
        lines.append(classname)
        lines.append(empty_line)

        last = len(self.fields) - 1
        for i, field in enumerate(self.fields):
            lines.extend(field.to_java_code(
                indent_spaces, self.type_classification))
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


SPECIFIC_TYPES: dict[frozenset[str], str] = {}
GENERATOR_STORAGE: list[TypeGenerator] = []
ADDITIONAL_TYPES: list[TypeGenerator] = []
DYNAMIC_IMPORTS: dict[str, TypeClassification] = {
    "InputFile": TypeClassification.DataType,
    "Id": TypeClassification.DataType,
}


class TypeGenerators:
    base_packagename: str

    def __init__(self, base_packagename: str) -> None:
        self.base_packagename = base_packagename

    def add_typegen(self, telegram_type: dict, type_classification: TypeClassification):
        typegen = TypeGenerator(telegram_type, type_classification)

        if typegen.name not in DYNAMIC_IMPORTS:
            DYNAMIC_IMPORTS[typegen.name] = type_classification

        GENERATOR_STORAGE.append(typegen)

    def __append_additional_types(self):
        for additional_type in ADDITIONAL_TYPES:
            if additional_type.name not in DYNAMIC_IMPORTS:
                DYNAMIC_IMPORTS[additional_type.name] = additional_type.type_classification

            if not additional_type.is_subtype:
                for subtype in cast(list[str], additional_type.subtypes):

                    for typegen in filter(lambda typegen: typegen.name == subtype, GENERATOR_STORAGE):
                        if typegen.subtype_of is not None:
                            typegen.subtype_of.append(additional_type.name)
                        else:
                            typegen.subtype_of = [additional_type.name]

                        if typegen.type_classification != additional_type.type_classification:
                            typegen.imports.add(
                                f"import {self.base_packagename}.{additional_type.type_classification.value}.{additional_type.name};")
                            additional_type.imports.add(
                                f"import {self.base_packagename}.{typegen.type_classification.value}.{typegen.name};")

            GENERATOR_STORAGE.append(additional_type)

        ADDITIONAL_TYPES.clear()

    def __ensure_dynamic_imports(self):
        for typegen in GENERATOR_STORAGE:
            typegen = cast(TypeGenerator, typegen)

            for field in typegen.fields:

                base_type = unwrap_type(field.type_)
                same_type = base_type in DYNAMIC_IMPORTS
                if not same_type:
                    continue

                if typegen.type_classification == DYNAMIC_IMPORTS[base_type]:
                    continue

                other_package = DYNAMIC_IMPORTS[base_type].package()
                typegen.imports.add(
                    f"import {self.base_packagename}.{other_package}.{base_type};")

    def __ensure_correctness(self):
        self.__append_additional_types()
        self.__ensure_dynamic_imports()

    def typegens(self) -> list[TypeGenerator]:
        self.__ensure_correctness()
        typegens = copy(GENERATOR_STORAGE)
        GENERATOR_STORAGE.clear()
        return typegens
