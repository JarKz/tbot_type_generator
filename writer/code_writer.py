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
        self.method_generator = MethodGenerator()
        self.base_packagename = base_packagename

    def add_type(self, type_: dict, type_classification: TypeClassification):
        self.type_geneartor.add_type(type_, type_classification)

    def add_method(self, raw_method: dict):
        self.method_generator.add_method(raw_method)

    @staticmethod
    def mkdir_if_missing(path: str):
        if not os.path.exists(path):
            os.makedirs(path)

    def write_all(self):
        types = self.type_geneartor.types()
        for type_ in types:
            extended_path = self.outdir + \
                type_.type_classification.package().replace(".", "/") + "/"

            CodeWriter.mkdir_if_missing(extended_path)

            filename = extended_path + type_.name + ".java"
            with open(filename, "w") as java_file:
                java_file.writelines(type_.to_java_code(self.base_packagename))

        methods_path = self.outdir + "/core/"
        CodeWriter.mkdir_if_missing(methods_path)
        filename = methods_path + "BotApi.java"
        with open(filename, "w") as java_file:
            self.method_generator.set_types(types)
            java_file.writelines(
                self.method_generator.build_java_class(self.base_packagename))

