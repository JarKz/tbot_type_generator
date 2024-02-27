from requests import get
import os
import json

from generators.typegen import TypeClassification, TypeGenerator
from generators.helpers import to_pascal_case

SPECS_PATH = "https://github.com/PaulSonOfLars/telegram-bot-api-spec/blob/main/api.json"
IGNORE_TYPES = [
    "InputFile"
]


def download_specs(output_file: str):
    response = get(url=SPECS_PATH)
    if response.status_code != 200:
        raise Exception("Can't download Telegram API specs!")

    with open(output_file, "w") as file:
        lines = response.json()["payload"]["blob"]["rawLines"]
        lines = map(lambda x: x + "\n", lines)
        file.writelines(lines)


def generate_types(output_dir: str, package_basename: str, api_specs: dict):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    typenames = api_specs["types"].keys()
    telegram_types = map(
        lambda typename: api_specs["types"][typename], typenames)

    for telegram_type in telegram_types:
        if telegram_type["name"] in IGNORE_TYPES:
            continue

        filename = output_dir + telegram_type["name"] + ".java"
        typegen = TypeGenerator(telegram_type, TypeClassification.DataType)

        with open(filename, "w") as java_file:
            java_file.writelines(typegen.to_text(
                package_basename + ".types"))


def generate_parameters(output_dir: str, package_basename: str, api_specs: dict):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    typenames = api_specs["methods"].keys()
    telegram_types = map(
        lambda typename: api_specs["methods"][typename], typenames)

    for telegram_type in telegram_types:
        telegram_type["name"] = to_pascal_case(
            telegram_type["name"]) + "Parameters"

        filename = output_dir + telegram_type["name"] + ".java"
        typegen = TypeGenerator(
            telegram_type, TypeClassification.MethodParameters)

        with open(filename, "w") as java_file:
            java_file.writelines(typegen.to_text(
                package_basename + ".core.parameters"))

    for typegen in TypeGenerator.ensure_additional_types():
        filename = output_dir + typegen.name + ".java"
        with open(filename, "w") as java_file:
            java_file.writelines(typegen.to_text(
                package_basename + ".core.parameters"))


if __name__ == "__main__":
    api_json_file = "api.json"
    download_specs(output_file=api_json_file)

    types_output_directory = "output/types/"
    parameters_output_directory = "output/parameters/"

    package_basename = "jarkz.tbot"

    with open(api_json_file, "r") as file:
        api_specs = json.load(file)
        generate_types(types_output_directory, package_basename, api_specs)
        generate_parameters(parameters_output_directory,
                            package_basename, api_specs)
