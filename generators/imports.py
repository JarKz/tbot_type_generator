from enum import Enum

class Imports(Enum):
    SerializedName = "import com.google.gson.annotations.SerializedName;"
    NotNull = "import jakarta.validation.constraints.NotNull;"
    Objects = "import java.util.Objects;"
    List = "import java.util.List;"
    MessageOrBoolean = "import jarkz.tbot.types.MessageOrBoolean;"
    Id = "import jarkz.tbot.types.Id;"
    InputFile = "import jarkz.tbot.types.InputFile;"

    def as_line(self) -> str:
        return self.value
