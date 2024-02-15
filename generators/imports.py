from enum import Enum

class Imports(Enum):
    SerializedName = "import com.google.gson.annotations.SerializedName;"
    NotNull = "import jakarta.validation.constraints.NotNull;"
    Objects = "import java.util.Objects;"
    List = "import java.util.List;"
