import os
from generators.methodgen import MethodGenerator
from generators.typegen import TypeGenerator, TypeClassification


BASE_PACKAGE_NAME = "jarkz.tbot"


class CodeWriter:
    type_geneartor: TypeGenerator
    method_generator: MethodGenerator
    outdir: str
    base_packagename: str

    def __init__(self, outdir: str, base_packagename: str = BASE_PACKAGE_NAME) -> None:
        self.outdir = outdir
        self.type_geneartor = TypeGenerator(base_packagename)
        self.base_packagename = base_packagename

    def add_type(self, type_: dict, type_classification: TypeClassification):
        self.type_geneartor.add_type(type_, type_classification)

    def write_all(self):
        for type_ in self.type_geneartor.types():
            extended_path = self.outdir + \
                type_.type_classification.package().replace(".", "/") + "/"

            if not os.path.exists(extended_path):
                os.makedirs(extended_path)

            filename = extended_path + type_.name + ".java"
            with open(filename, "w") as java_file:
                java_file.writelines(type_.to_java_code(self.base_packagename))
