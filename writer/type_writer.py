import os
from generators.typegen import Generators, TypeClassification


BASE_PACKAGE_NAME = "jarkz.tbot"


class WriterTypes:
    geneartors: Generators
    outdir: str
    base_packagename: str

    def __init__(self, outdir: str, base_packagename: str = BASE_PACKAGE_NAME) -> None:
        self.outdir = outdir
        self.geneartors = Generators(base_packagename)
        self.base_packagename = base_packagename

    def add_type(self, type_: dict, type_classification: TypeClassification):
        self.geneartors.add_typegen(type_, type_classification)

    def write_all(self):
        for typegen in self.geneartors.typegens():
            extended_path = self.outdir + \
                typegen.type_classification.value.replace(".", "/") + "/"

            if not os.path.exists(extended_path):
                os.makedirs(extended_path)

            filename = extended_path + typegen.name + ".java"
            with open(filename, "w") as java_file:
                java_file.writelines(typegen.to_text(self.base_packagename))
