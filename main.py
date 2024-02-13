from requests import get
import os
import json

from generators.typegen import TypeGenerator

SPECS_PATH = "https://github.com/PaulSonOfLars/telegram-bot-api-spec/blob/main/api.json"


def download_specs(output_file: str):
    response = get(url=SPECS_PATH)
    if response.status_code != 200:
        raise Exception("Can't download Telegram API specs!")

    with open(output_file, "w") as file:
        lines = response.json()["payload"]["blob"]["rawLines"]
        lines = map(lambda x: x + "\n", lines)
        file.writelines(lines)


if __name__ == "__main__":
    api_json_file = "api.json"
    download_specs(output_file=api_json_file)

    types_output_directory = "output/types/"

    if not os.path.exists(types_output_directory):
        os.makedirs(types_output_directory)

    with open(api_json_file, "r") as file:
        api_specs = json.load(file)

        typenames = api_specs["types"].keys()
        telegram_types = map(
            lambda typename: api_specs["types"][typename], typenames)

        for telegram_type in telegram_types:
            filename = types_output_directory + telegram_type["name"] + ".java"
            typegen = TypeGenerator(telegram_type)

            with open(filename, "w") as java_file:
                java_file.writelines(typegen.to_text(
                    package_name="jarkz.tbot.types"))

