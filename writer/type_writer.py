import os
from typing import cast
from generators.typegen import TypeClassification, TypeGenerator


BASE_PACKAGE_NAME = "jarkz.tbot"


class WriterTypes:
    typegens: list[TypeGenerator]
    outdir: str
    package_basename: str

    def __init__(self, outdir: str, package_basename: str) -> None:
        self.typegens = []
        self.outdir = outdir
        self.package_basename = package_basename

    def add_type(self, type_: dict, type_classification: TypeClassification):
        self.typegens.append(TypeGenerator(
            type_, type_classification))

    def __ensure_correctness(self):
        additional_types: list[TypeGenerator] = TypeGenerator.ensure_additional_types(
        )

        for additional_type in additional_types:
            if not additional_type.is_subtype:
                for subtype in cast(list[str], additional_type.subtypes):

                    for typegen in filter(lambda typegen: typegen.name == subtype, self.typegens):
                        typegen.imports.add(
                            f"import {self.package_basename}.{additional_type.type_classification.value}.{additional_type.name};")
                        if typegen.subtype_of is not None:
                            typegen.subtype_of.append(additional_type.name)
                        else:
                            typegen.subtype_of = [additional_type.name]

                        additional_type.imports.add(
                            f"import {self.package_basename}.{typegen.type_classification.value}.{typegen.name};")

            self.typegens.append(additional_type)

    def write_all(self):
        self.__ensure_correctness()

        for typegen in self.typegens:
            extended_path = self.outdir + \
                typegen.type_classification.value.replace(".", "/") + "/"

            if not os.path.exists(extended_path):
                os.makedirs(extended_path)

            filename = extended_path + typegen.name + ".java"
            with open(filename, "w") as java_file:
                java_file.writelines(typegen.to_text(self.package_basename))
