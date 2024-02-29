import os
from generators.methodgen import MethodGenerators
from generators.typegen import TypeGenerators, TypeClassification


BASE_PACKAGE_NAME = "jarkz.tbot"

class CodeWriter:
    type_geneartors: TypeGenerators
    method_generators: MethodGenerators
    outdir: str
    base_packagename: str

    def __init__(self, outdir: str, base_packagename: str = BASE_PACKAGE_NAME) -> None:
        self.outdir = outdir
        self.type_geneartors = TypeGenerators(base_packagename)
        self.base_packagename = base_packagename

    def add_type(self, type_: dict, type_classification: TypeClassification):
        self.type_geneartors.add_typegen(type_, type_classification)


    def write_all(self):
        for typegen in self.type_geneartors.typegens():
            extended_path = self.outdir + \
                typegen.type_classification.value.replace(".", "/") + "/"

            if not os.path.exists(extended_path):
                os.makedirs(extended_path)

            filename = extended_path + typegen.name + ".java"
            with open(filename, "w") as java_file:
                java_file.writelines(typegen.to_text(self.base_packagename))
