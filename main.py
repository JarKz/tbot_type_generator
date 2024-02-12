from requests import get
import os
import json

SPECS_PATH = "https://github.com/PaulSonOfLars/telegram-bot-api-spec/blob/main/api.json"


def download_specs(output_file: str):
    response = get(url=SPECS_PATH)
    if response.status_code != 200:
        raise Exception("Can't download Telegram API specs!")

    with open(output_file, "w") as file:
        lines = response.json()["payload"]["blob"]["rawLines"]
        lines = map(lambda x: x + "\n", lines)
        file.writelines(lines)


def generate_description(phrases: list[str], ident: str) -> str:
    description = f"{ident}/**\n"
    for phrase in phrases:
        description += f"{ident}* {phrase}\n*\n"
    description += "*/\n"
    return description


def to_camel_case(field_name: str) -> str:
    words = field_name.split("_")
    if len(words) == 1:
        return field_name

    new_name = words[0]
    for word in words[1:]:
        new_name += word[0].upper() + word[1:]
    return new_name


def map_type(original_type: str, required: bool) -> str:
    return_value = {
        True: {
            "True": "boolean",
            "Float number": "float",
            "Integer": "int",
            "String": "String",
            "Boolean": "boolean",
            "Float": "float"
        },
        False: {
            "True": "Boolean",
            "Float number": "Float",
            "Integer": "Integer",
            "String": "String",
            "Boolean": "Boolean",
            "Float": "Float"
        }
    }

    if len(original_type) == 1:
        if original_type[0] in return_value[required]:
            return return_value[required][original_type[0]]
        else:
            return original_type[0]

    if original_type == ["Integer", "String"]:
        return "String"
    elif original_type == ["InputFile", "String"]:
        return "InputFile"

    raise Exception("Unknown type!")


def generate_type(telegram_type: dict, package_name: str) -> list[str]:
    classname = telegram_type["name"]

    lines = []
    lines.append(f"package {package_name}.{classname};\n")

    empty_line = "\n"
    for _ in range(2):
        lines.append(empty_line)

    lines.append(generate_description(telegram_type["description"], ""))

    if telegram_type.get("subtypes") is not None:
        subtypes = ", ".join(telegram_type["subtypes"])
        lines.append(
            f"sealed public interface {classname} permits {subtypes} {{}}")
        return lines

    classname = "public final class " + classname

    if telegram_type.get("subtype_of") is not None:
        if len(telegram_type["subtype_of"]) > 1:
            raise Exception(
                "Expected one subtype_of, but given many subtype_of!")
        classname += " implements " + telegram_type["subtype_of"][0]

    classname += " {\n"
    lines.append(classname)
    lines.append(empty_line)

    used_annotations = set()

    ident = "  "
    for field in telegram_type.get("fields", []):
        lines.append(ident + "/** " + field["description"] + " */\n")
        field_name = field["name"]
        camel_cased_field_name = to_camel_case(field_name)
        if camel_cased_field_name != field_name:
            lines.append(ident + "@SerializedName(\"" + field_name + "\")\n")
            used_annotations.add(
                "import com.google.gson.annotations.SerializedName;\n")

        is_required = field["required"]
        if is_required:
            lines.append(ident + "@NotNull\n")
            used_annotations.add(
                "import jakarta.validation.contraints.NotNull;\n")

        field_type = map_type(field["types"], is_required)
        field_line = f"{ident}public {field_type} {camel_cased_field_name};\n\n"
        lines.append(field_line)

    if len(used_annotations) > 0:
        empty_line = "\n"
        lines.insert(2, empty_line)

        for import_annotation in used_annotations:
            lines.insert(2, import_annotation)
        ...

    lines.append("}")
    return lines


if __name__ == "__main__":
    api_json_file = "api.json"
    download_specs(output_file=api_json_file)

    types_output_directory = "output/types/"

    if not os.path.exists(types_output_directory):
        os.makedirs(types_output_directory)

    with open(api_json_file, "r") as file:
        api_specs = json.load(file)

        typenames = api_specs["types"].keys()
        for typename in typenames:
            telegram_type = api_specs["types"][typename]
            filename = types_output_directory + telegram_type["name"] + ".java"
            with open(filename, "w") as java_file:
                java_file.writelines(generate_type(
                    telegram_type, package_name="jarkz.tbot.types"))
