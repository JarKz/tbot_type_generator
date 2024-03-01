from requests import get
from copy import deepcopy
import json

from generators.typegen import TypeClassification
from generators.helpers import to_pascal_case
from writer.code_writer import CodeWriter

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


def add_datatypes(writer: CodeWriter, specs: dict):
    datatype_names = specs["types"].keys()
    datatypes = map(lambda name: specs["types"][name], datatype_names)

    for datatype in datatypes:

        if datatype["name"] in IGNORE_TYPES:
            continue

        writer.add_type(datatype, TypeClassification.DataType)


def add_method_params(writer: CodeWriter, specs: dict):
    method_names = specs["methods"].keys()
    methods = map(lambda name: deepcopy(specs["methods"][name]), method_names)

    for method_params in methods:
        if "fields" not in method_params:
            continue

        method_params["name"] = to_pascal_case(
            method_params["name"]) + "Parameters"
        writer.add_type(method_params, TypeClassification.MethodParameters)


if __name__ == "__main__":
    api_json_file = "api.json"
    download_specs(output_file=api_json_file)

    output_dir = "output/"

    with open(api_json_file, "r") as file:
        api_specs = json.load(file)

        writer = CodeWriter(output_dir)

        add_datatypes(writer, api_specs)
        add_method_params(writer, api_specs)

        writer.write_all()
