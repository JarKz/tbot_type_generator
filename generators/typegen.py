from functools import reduce
from typing import cast
from copy import copy
from enum import Enum
import re

from .helpers import *
from generators.constants import EMPTY_LINE, ARRAY_OF


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

    is_constant: bool
    constant_data: str | None

    def __init__(self, field: dict) -> None:
        self.__parse(field)

    def __parse_constant_data(self):
        regexs = [re.compile("must be \\w*$"),
                  re.compile("always \"\\w*\"$")]
        for regex in regexs:
            match = regex.findall(self.description)
            if match:
                data: str = match[0].split(" ")[-1]
                if not data.startswith('"'):
                    data = '"' + data + '"'

                self.is_constant = True
                self.constant_data = data
                return

        self.is_constant = False
        self.constant_data = None

    def __parse(self, field: dict):
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

        self.__parse_constant_data()

    def to_java_code(self, indent_spaces: int, type_classification: TypeClassification) -> list[str]:
        indent = " " * indent_spaces

        lines = []
        if self.is_constant and type_classification == TypeClassification.DataType:
            lines = [
                f"{indent}public static final {self.type_} {self.name.upper()} = {self.constant_data};\n",
                EMPTY_LINE,
            ]

        lines.append(f"{indent}/** {self.description} */\n")

        for annotation in self.annotations:
            lines.append(f"{indent}{annotation}\n")

        field_line = f"{indent}public "
        if self.is_constant:
            field_line += f" final {self.type_} {self.camel_cased_name} = {self.name.upper()};\n"
        else:
            field_line += f"{self.type_} {self.camel_cased_name};\n"

        lines.append(field_line)

        return lines


class Type:
    name: str
    description: list[str]
    fields: list[Field]
    is_supertype: bool
    subtype_of: None | list[str]
    subtypes: None | list[str]
    imports: set[str]

    DEFAULT_TYPE_CLASSIFICATION = TypeClassification.DataType
    type_classification: TypeClassification

    def __init__(self, telegram_type: dict, type_classification: None | TypeClassification = None):
        if type_classification is None:
            self.__parse(telegram_type, self.DEFAULT_TYPE_CLASSIFICATION)
        else:
            self.__parse(telegram_type, type_classification)

    def __create_new_interface(self, raw_field: dict) -> str:
        types: list[str] = raw_field["types"]
        name = to_pascal_case(raw_field["name"])

        new_type = name
        data = {
            "name": name,
            "description": "",
            "subtypes": types,
        }
        if all(map(lambda typename: typename.startswith(ARRAY_OF), types)):
            new_type = ARRAY_OF + name
            data["subtypes"] = list(
                map(lambda type_: type_[len(ARRAY_OF):], types))

        GROUPED_INTERFACES.append(Type(
            data, Type.DEFAULT_TYPE_CLASSIFICATION))
        SPECIFIC_TYPES[frozenset(types)] = name

        return new_type

    def __parse_fields(self, raw_fields: list[dict]):
        def datatype_fields(raw_fields: list[dict]) -> list[Field]:
            fields = map(lambda raw_field: Field(raw_field), raw_fields)
            return list(fields)

        def method_parameters_fields(raw_fields: list[dict]) -> list[Field]:
            fields = []
            for raw_field in raw_fields:
                types = frozenset(raw_field["types"])

                if types in SPECIFIC_TYPES:
                    raw_field["types"] = [SPECIFIC_TYPES[types]]
                elif len(types) > 2:
                    new_type = self.__create_new_interface(raw_field)
                    raw_field["types"] = [new_type]

                fields.append(Field(raw_field))
            return fields

        fields: list[Field]
        match self.type_classification:
            case TypeClassification.DataType:
                fields = datatype_fields(raw_fields)
            case TypeClassification.MethodParameters:
                fields = method_parameters_fields(raw_fields)
            case _:
                raise Exception("Non-exhaustive enum TypeClassification!")

        self.fields = fields

    def __parse(self, telegram_type: dict, type_classification: TypeClassification):
        self.type_classification = type_classification

        self.name = telegram_type["name"]
        self.description = telegram_type["description"]

        self.subtypes = telegram_type.get("subtypes")
        if self.subtypes is None:

            self.is_supertype = False

            self.subtype_of = telegram_type.get("subtype_of")
            if self.subtype_of is not None and len(self.subtype_of) > 1:
                raise Exception(
                    "Expected one subtype_of, but given many subtype_of!")

        else:
            self.is_supertype = True

        self.imports = set()
        self.__parse_fields(telegram_type.get("fields", []))

    def make_builder(self, indent_spaces: int) -> list[str]:
        indent = " " * indent_spaces
        instanceName = "buildingType"
        lines = [
            f"{indent}public static final class Builder {{\n",
            EMPTY_LINE,
            f"{indent * 2}private {self.name} {instanceName};\n",
            EMPTY_LINE,
            f"{indent * 2}public Builder() {{\n",
            f"{indent * 3}buildingType = new {self.name}();\n",
            f"{indent * 2}}}\n",
        ]

        for field in self.fields:
            methodName = to_pascal_case(field.name)

            if field.type_ == "boolean" and methodName.startswith("Is"):
                methodName = methodName[2:]
            methodName = "set" + methodName

            lines.extend([
                EMPTY_LINE,
                f"{indent * 2}public Builder {methodName}({field.type_} {field.camel_cased_name}) {{\n",
                f"{indent * 3}{instanceName}.{field.camel_cased_name} = {field.camel_cased_name};\n"
                f"{indent * 3}return this;\n",
                f"{indent * 2}}}\n",
            ])

        lines.extend([
            EMPTY_LINE,
            f"{indent * 2}public {self.name} build() {{\n",
            f"{indent * 3}return {instanceName};\n",
            f"{indent * 2}}}\n",
            f"{indent}}}\n",
            EMPTY_LINE
        ])

        return lines

    def make_method_equals(self, indent_spaces: int) -> list[str]:
        indent = " " * indent_spaces
        lines = [
            f"{indent}@Override\n",
            f"{indent}public final boolean equals(Object obj) {{\n"
            f"{indent * 2}if (this == obj) return true;\n"
        ]

        if not self.fields:
            lines.append(
                f"{indent * 2}if (!(obj instanceof {self.name})) return false;\n")
            lines.append(f"{indent * 2}return true;\n")
            lines.append(f"{indent}}}\n")
            return lines

        lines.append(
            f"{indent * 2}if (!(obj instanceof {self.name} other)) return false;\n")

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
        indent_spaces = 2

        equals_method = self.make_method_equals(indent_spaces)
        hash_code_method = self.make_method_hash_code(indent_spaces)
        to_string_method = self.make_method_to_string(indent_spaces)

        all_imports = map(lambda field: field.imports, self.fields)
        self.imports = reduce(lambda lhs, rhs: lhs.union(
            rhs), all_imports, self.imports)

        if len(self.imports) > 0:
            lines.append(EMPTY_LINE)
            for used_import in self.imports:
                lines.append(used_import + "\n")

        for _ in range(2):
            lines.append(EMPTY_LINE)

        lines.append(generate_description(self.description, indent_spaces=0))

        if self.is_supertype:
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
        lines.append(EMPTY_LINE)

        lines.extend(self.make_builder(indent_spaces))

        last = len(self.fields) - 1
        for i, field in enumerate(self.fields):
            lines.extend(field.to_java_code(
                indent_spaces, self.type_classification))
            if i != last:
                lines.append(EMPTY_LINE)

        lines.append(EMPTY_LINE)
        lines.extend(equals_method)
        lines.append(EMPTY_LINE)
        lines.extend(hash_code_method)
        lines.append(EMPTY_LINE)
        lines.extend(to_string_method)

        lines.append("}")

        return lines


SPECIFIC_TYPES: dict[frozenset[str], str] = {}
TYPE_STORAGE: list[Type] = []
GROUPED_INTERFACES: list[Type] = []
DYNAMIC_IMPORTS: dict[str, TypeClassification] = {
    "InputFile": TypeClassification.DataType,
    "Id": TypeClassification.DataType,
    "MessageOrBoolean": TypeClassification.DataType,
}


class TypeGenerator:
    base_packagename: str

    def __init__(self, base_packagename: str) -> None:
        self.base_packagename = base_packagename

    @staticmethod
    def __put_dynamic_import_if_absent(type_: Type) -> None:
        if type_.name not in DYNAMIC_IMPORTS:
            DYNAMIC_IMPORTS[type_.name] = type_.type_classification

    def add_type(self, telegram_type: dict, type_classification: TypeClassification):
        type_ = Type(telegram_type, type_classification)

        TypeGenerator.__put_dynamic_import_if_absent(type_)

        TYPE_STORAGE.append(type_)

    def __append_grouped_interfaces(self) -> None:
        def bind(type_: Type, supertype: Type) -> None:
            if type_.subtype_of is not None:
                type_.subtype_of.append(supertype.name)
            else:
                type_.subtype_of = [supertype.name]

        def bind_interface_and_subtypes(interface: Type):
            for subtype in cast(list[str], interface.subtypes):

                for type_ in filter(lambda type_: type_.name == subtype, TYPE_STORAGE):
                    bind(type_, interface)

        for new_interface in GROUPED_INTERFACES:
            TypeGenerator.__put_dynamic_import_if_absent(new_interface)

            if new_interface.is_supertype:
                bind_interface_and_subtypes(new_interface)

            TYPE_STORAGE.append(new_interface)

        GROUPED_INTERFACES.clear()

    def __ensure_dynamic_imports(self):
        for type_ in TYPE_STORAGE:
            type_ = cast(Type, type_)

            for field in type_.fields:

                base_type = unwrap_type(field.type_)
                same_type = base_type in DYNAMIC_IMPORTS
                if not same_type:
                    continue

                if type_.type_classification == DYNAMIC_IMPORTS[base_type]:
                    continue

                other_package = DYNAMIC_IMPORTS[base_type].package()
                type_.imports.add(
                    f"import {self.base_packagename}.{other_package}.{base_type};")

    def __ensure_correctness(self):
        self.__append_grouped_interfaces()
        self.__ensure_dynamic_imports()

    def types(self) -> list[Type]:
        self.__ensure_correctness()
        types = copy(TYPE_STORAGE)
        TYPE_STORAGE.clear()
        return types
