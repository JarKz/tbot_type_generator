from enum import Enum

class Imports(Enum):
    SerializedName = "import com.google.gson.annotations.SerializedName;"
    Objects = "import java.util.Objects;"
    List = "import java.util.List;"
    MessageOrBoolean = "import jarkz.tbot.types.MessageOrBoolean;"
    Id = "import jarkz.tbot.types.Id;"
    NotNull = "import jarkz.tbot.types.annotations.NotNull;"
    InputFile = "import jarkz.tbot.types.InputFile;"

    def as_line(self) -> str:
        return self.value
