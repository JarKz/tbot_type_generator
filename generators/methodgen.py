from enum import Enum
from functools import reduce
from typing import Iterable
from generators.constants import EMPTY_LINE
from generators.helpers import map_type, to_pascal_case, unwrap_type
from generators.typegen import Type, TypeClassification

PACKAGE = "core"

IMPORTS = {
    "import com.google.common.reflect.TypeToken;",
    "import com.google.gson.Gson;",
    "import com.google.gson.GsonBuilder;",
    "import com.google.gson.annotations.SerializedName;",
    "import java.io.IOException;",
    "import java.lang.reflect.Field;",
    "import java.net.URI;",
    "import java.nio.charset.Charset;",
    "import java.util.LinkedList;",
    "import java.util.List;",
    "import java.util.Set;",
    "import java.util.function.Consumer;",
    "import org.apache.http.HttpEntity;",
    "import org.apache.http.HttpResponse;",
    "import org.apache.http.client.methods.HttpPost;",
    "import org.apache.http.entity.ContentType;",
    "import org.apache.http.entity.StringEntity;",
    "import org.apache.http.entity.mime.MultipartEntityBuilder;",
    "import org.apache.http.impl.client.CloseableHttpClient;",
    "import org.apache.http.impl.client.HttpClients;",
}

CLASSNAME = "BotApi"

CLASS_DOCUMENTATION = [
    "/**",
    " * General implementation of data exchanging between Appication and Telegram API using HTTP",
    " * requests.",
    " *",
    " * <p>This class contains several methods of Telegram API. For passing parameters to method use",
    " * specific type, which creates from method name in PascalCase + \"Parameters\" word (e.g.",
    " * \"getUpdates\" method -> \"GetUpdatesParameters\"). Theses parameters contains required fields and",
    " * optional fields, which can sets by setters. <strong>Note:</strong> exception will be thrown if",
    " * one of required fields is not set.",
    " *",
    " * <p>Usage:",
    " *",
    " * <pre><code>",
    " * var token = \"your_token\";",
    " * var api = new BotApi(token);",
    " * var params = new GetUpdatesParameters();",
    " * {@link Update}[] updates = api.getUpdates(params);",
    " * </code></pre>",
    " */",
]

DEFAULT_LINES_AT_START = [
    "   private static final Gson gson;",
    "",
    "   static {",
    "     gson = registerAllAdapters();",
    "   }",
    "",
    "   private static final Set<Class<?>> DEFAULT_TYPES =",
    "       Set.of(",
    "           String.class,",
    "           Short.class,",
    "           Integer.class,",
    "           Long.class,",
    "           Float.class,",
    "           Double.class,",
    "           Character.class,",
    "           Boolean.class,",
    "           Byte.class,",
    "           Short.TYPE,",
    "           Integer.TYPE,",
    "           Long.TYPE,",
    "           Float.TYPE,",
    "           Double.TYPE,",
    "           Character.TYPE,",
    "           Boolean.TYPE,",
    "           Byte.TYPE);",
    "",
    "   private static Gson registerAllAdapters() {",
    "     return new GsonBuilder()",
    "         .registerTypeAdapter(",
    "             jarkz.tbot.types.BotCommandScope.class,",
    "             new jarkz.tbot.types.deserializers.BotCommandScopeDeserializer())",
    "         .registerTypeAdapter(",
    "             jarkz.tbot.types.ChatMember.class,",
    "             new jarkz.tbot.types.deserializers.ChatMemberDeserializer())",
    "         .registerTypeAdapter(",
    "             jarkz.tbot.types.MenuButton.class,",
    "             new jarkz.tbot.types.deserializers.MenuButtonDeserializer())",
    "         .registerTypeAdapter(",
    "             jarkz.tbot.types.MessageOrigin.class,",
    "             new jarkz.tbot.types.deserializers.MessageOriginDeserializer())",
    "         .registerTypeAdapter(",
    "             jarkz.tbot.types.ReactionType.class,",
    "             new jarkz.tbot.types.deserializers.ReactionTypeDeserializer())",
    "         .registerTypeAdapter(",
    "             jarkz.tbot.types.MaybeInaccessibleMessage.class,",
    "             new jarkz.tbot.types.deserializers.MaybeInaccessibleMessageDeserializer())",
    "         .registerTypeAdapter(",
    "             jarkz.tbot.types.ChatBoostSource.class,",
    "             new jarkz.tbot.types.deserializers.ChatBoostSourceDeserializer())",
    "         .registerTypeAdapter(",
    "             jarkz.tbot.types.PassportElementError.class,",
    "             new jarkz.tbot.types.deserializers.PassportElementErrorDeserializer())",
    "         .registerTypeAdapter(",
    "             jarkz.tbot.types.InputFile.class,",
    "             new jarkz.tbot.types.serializers.InputFileSerializer())",
    "         .create();",
    "   }",
    "",
    "   private final String botToken;",
    "",
    "   private final String urlTemplate = \"https://api.telegram.org/bot%s/%s\";",
    "",
    "   public BotApi(String botToken) {",
    "     this.botToken = botToken;",
    "   }",
]

DEFAULT_LINES_AT_END = [
    "  private Response makeRequest(String methodName, StringEntity paramsAsEntity) {",
    "    HttpPost request = new HttpPost(getUri(methodName));",
    "    request.setEntity(paramsAsEntity);",
    "    request.setHeader(\"Accept\", \"application/json\");",
    "    request.setHeader(\"Content-Type\", \"application/json\");",
    "",
    "    try (CloseableHttpClient client = HttpClients.createDefault()) {",
    "      HttpResponse httpResponse = client.execute(request);",
    "      return gson.fromJson(",
    "          new String(httpResponse.getEntity().getContent().readAllBytes()), Response.class);",
    "    } catch (IOException e) {",
    "      throw new RuntimeException(e);",
    "    }",
    "  }",
    "",
    "  private Response makeMultipartFormRequest(String methodName, HttpEntity paramsAsEntity) {",
    "    HttpPost request = new HttpPost(getUri(methodName));",
    "    request.setEntity(paramsAsEntity);",
    "",
    "    try (CloseableHttpClient client = HttpClients.createDefault()) {",
    "      HttpResponse httpResponse = client.execute(request);",
    "      return gson.fromJson(",
    "          new String(httpResponse.getEntity().getContent().readAllBytes()), Response.class);",
    "    } catch (IOException e) {",
    "      throw new RuntimeException(e);",
    "    }",
    "  }",
    "",
    "  private HttpEntity buildMultipartEntity(Object params) {",
    "    final var type = params.getClass();",
    "    final var fields = type.getDeclaredFields();",
    "    final var form = MultipartEntityBuilder.create();",
    "",
    "    for (final var field : fields) {",
    "      var name = field.getName();",
    "      if (field.isAnnotationPresent(SerializedName.class)) {",
    "        var annotation = field.getAnnotation(SerializedName.class);",
    "        name = annotation.value();",
    "      }",
    "",
    "      Object data = null;",
    "      try {",
    "        data = field.get(params);",
    "      } catch (IllegalAccessException e) {",
    "        throw new RuntimeException(\"Fields in Parameters type must be public!\");",
    "      }",
    "",
    "      if (data instanceof InputFile inputFile) {",
    "        switch (inputFile.type()) {",
    "          case FILE_ID -> form.addTextBody(name, inputFile.fileId());",
    "          case BYTES -> form.addBinaryBody(name, inputFile.bytes());",
    "          case FILE -> form.addBinaryBody(name, inputFile.file());",
    "        }",
    "      } else {",
    "        form.addTextBody(name, gson.toJson(data), ContentType.APPLICATION_JSON);",
    "      }",
    "    }",
    "",
    "    return form.build();",
    "  }",
    "",
    "  private HttpEntity buildExtendedMultipartEntity(Object params) {",
    "    final var type = params.getClass();",
    "    final var fields = type.getDeclaredFields();",
    "    final var form = MultipartEntityBuilder.create();",
    "    final var inputFiles = new LinkedList<InputFile>();",
    "",
    "    for (final var field : fields) {",
    "      var name = field.getName();",
    "      if (field.isAnnotationPresent(SerializedName.class)) {",
    "        var annotation = field.getAnnotation(SerializedName.class);",
    "        name = annotation.value();",
    "      }",
    "",
    "      Object data = null;",
    "      try {",
    "        data = field.get(params);",
    "      } catch (IllegalAccessException e) {",
    "        throw new RuntimeException(\"Fields in Parameters type must be public!\");",
    "      }",
    "",
    "      // This code is valid, even when type contains InputFile type, because serializer puts file",
    "      // attachment name or file_id and I can get it, when needs.",
    "      form.addTextBody(name, gson.toJson(data), ContentType.APPLICATION_JSON);",
    "      getAllInputFiles(field, params, inputFiles);",
    "    }",
    "",
    "    for (var inputFile : inputFiles) {",
    "      switch (inputFile.type()) {",
    "        case FILE_ID -> {",
    "          /* Do nothing */",
    "        }",
    "        case BYTES -> form.addBinaryBody(inputFile.attachmentName(), inputFile.bytes());",
    "        case FILE -> form.addBinaryBody(inputFile.attachmentName(), inputFile.file());",
    "      }",
    "    }",
    "",
    "    return form.build();",
    "  }",
    "",
    "  private void getAllInputFiles(Field field, Object object, List<InputFile> inputFiles) {",
    "    final var type = field.getType();",
    "    if (DEFAULT_TYPES.contains(type)) {",
    "      return;",
    "    }",
    "    Consumer<Object> findRecursive =",
    "        (otherObject) -> {",
    "          for (var otherField : otherObject.getClass().getDeclaredFields()) {",
    "            getAllInputFiles(otherField, otherObject, inputFiles);",
    "          }",
    "        };",
    "",
    "    Object data = null;",
    "    try {",
    "      data = field.get(object);",
    "    } catch (IllegalAccessException e) {",
    "      throw new RuntimeException(\"Fields in Parameters type must be public!\");",
    "    }",
    "    if (data == null) {",
    "      return;",
    "    }",
    "",
    "    if (data instanceof List list) {",
    "      for (var otherObject : list) {",
    "        findRecursive.accept(otherObject);",
    "      }",
    "      return;",
    "    }",
    "",
    "    if (data instanceof InputFile inputFile) {",
    "      inputFiles.add(inputFile);",
    "      return;",
    "    }",
    "",
    "    findRecursive.accept(data);",
    "  }",
    "",
    "  private void raiseRuntimeException(Response response) {",
    "    throw new RuntimeException(",
    "        response.getDescription().isPresent()",
    "            ? response.getDescription().orElseThrow()",
    "            : String.valueOf(response.getErrorCode().orElseThrow()));",
    "  }",
    "",
    "  private URI getUri(String methodName) {",
    "    return URI.create(String.format(urlTemplate, botToken, methodName));",
    "  }",
]


class FindState(Enum):
    NotFound = 0
    Found = 1
    DeepFound = 2


class Method:
    name: str
    parameter_name: str
    description: str
    href: str
    return_type: str
    imports: set[str]
    arguments_exists: bool

    def __init__(self, raw_method: dict) -> None:
        self.__parse(raw_method)

    def __parse(self, raw_method: dict) -> None:
        self.name = raw_method["name"]
        self.parameter_name = to_pascal_case(self.name) + "Parameters"
        self.href = raw_method["href"]
        self.description = raw_method["description"]

        self.return_type, self.imports = map_type(
            raw_method["returns"], required=False)
        self.arguments_exists = "fields" in raw_method

    def __find_input_file_field(self, type_: Type, types: list[Type], _level: int = 1) -> FindState:
        for field in type_.fields:
            unwrapped_type = unwrap_type(field.type_)

            if unwrapped_type == "InputFile":
                return FindState(min(_level, 2))

            inner_type = next(
                filter(lambda inner_type: inner_type.name == unwrapped_type, types), None)

            if inner_type is None:
                continue

            self.__find_input_file_field(inner_type, types, _level + 1)

        return FindState.NotFound

    def __build_entity_and_request_lines(self, indent: str, state: FindState) -> list[str]:
        match state:
            case FindState.NotFound:
                return [
                    f"{indent}final var entity = new StringEntity(gson.toJson(params), Charset.forName(\"UTF-8\"));\n"
                    f"{indent}var response = makeRequest(methodName, entity);\n"
                ]
            case FindState.Found:
                return [
                    f"{indent}final var entity = buildMultipartEntity(params);\n"
                    f"{indent}var response = makeMultipartFormRequest(methodName, entity);\n"
                ]
            case FindState.DeepFound:
                return [
                    f"{indent}final var entity = buildExtendedMultipartEntity(params);\n"
                    f"{indent}var response = makeMultipartFormRequest(methodName, entity);\n"
                ]
            case _:
                raise Exception(
                    "The enum FindState match is not exhaustive!")

    def create_body(self, types: list[Type], indent_spaces: int) -> list[str]:
        indent = " " * indent_spaces

        lines: list[str]
        if self.arguments_exists:
            lines = [
                f"{indent}public {self.return_type} {self.name}({self.parameter_name} params) {{\n",
            ]
        else:
            lines = [
                f"{indent}public {self.return_type} {self.name}() {{\n",
            ]

        lines.extend([
            f"{indent * 2}final var methodName = \"{self.name}\";\n",
            EMPTY_LINE
        ])

        if self.arguments_exists:
            type_ = next(filter(lambda type_: type_.name ==
                         self.parameter_name, types))
            state = self.__find_input_file_field(type_, types)
            lines.extend(
                self.__build_entity_and_request_lines(indent * 2, state))
        else:
            lines.extend([
                f"{indent * 2}final var entity = new StringEntity(\"\", Charset.forName(\"UTF-8\"));\n",
                f"{indent * 2}var response = makeRequest(methodName, entity);\n"
            ])

        lines.extend([
            EMPTY_LINE,
            f"{indent * 2}if (!response.isOk()) {{\n",
            f"{indent * 3}raiseRuntimeException(response);\n",
            f"{indent * 2}}}\n",
            EMPTY_LINE,
            f"{indent * 2}var type = new TypeToken<{self.return_type}>() {{}}.getType();\n",
            f"{indent * 2}var jsonElement =\n",
            f"{indent * 4}response.getResult().orElseThrow(() -> new RuntimeException(\"Invalid result of response.\"));\n",
            EMPTY_LINE,
            f"{indent * 2}return gson.fromJson(jsonElement, type);\n",
            f"{indent}}}\n",
        ])

        return lines


class MethodGenerator:
    types: list[Type]
    methods: list[Method]

    def __init__(self) -> None:
        self.methods = []

    def set_types(self, types: list[Type]) -> None:
        self.types = types

    def add_method(self, raw_method: dict) -> None:
        self.methods.append(Method(raw_method))

    def build_java_class(self, base_packagename: str) -> list[str]:

        def append_new_lines(data: Iterable[str]) -> list[str]:
            return list(map(lambda line: line + "\n", data))

        def get_import_params(base_packagename: str, types: list[Type]) -> list[str]:
            parameters = filter(lambda type_: type_.type_classification ==
                                TypeClassification.MethodParameters, types)
            return list(map(
                lambda param: f"import {base_packagename}.{param.type_classification.package()}.{param.name};\n", parameters))

        def get_import_types(base_packagename: str, methods: list[Method], types: list[Type]):
            imports = set()
            for method in methods:
                type_to_import = next(
                    filter(lambda type_: type_.name == method.return_type, types), None)

                if type_to_import is None:
                    continue

                imports.add(
                    f"import {base_packagename}.{type_to_import.type_classification.package()}.{type_to_import.name};\n")

            return imports

        lines: list[str] = [
            f"package {base_packagename}.{PACKAGE};\n",
            EMPTY_LINE
        ]

        lines.extend(append_new_lines(IMPORTS))

        import_set = map(lambda method: method.imports, self.methods)
        specific_imports = reduce(
            lambda i1, i2: i1.union(i2), import_set, set())
        lines.extend(append_new_lines(specific_imports))

        lines.extend(get_import_params(base_packagename, self.types))
        lines.extend(get_import_types(
            base_packagename, self.methods, self.types))

        lines.append(EMPTY_LINE)
        lines.extend(append_new_lines(CLASS_DOCUMENTATION))

        lines.extend([
            EMPTY_LINE,
            f"public final class {CLASSNAME} {{\n",
            EMPTY_LINE
        ])

        lines.extend(append_new_lines(DEFAULT_LINES_AT_START))
        lines.append(EMPTY_LINE)

        for method in self.methods:
            lines.extend(method.create_body(self.types,  indent_spaces=2))
            lines.append(EMPTY_LINE)

        lines.extend(append_new_lines(DEFAULT_LINES_AT_END))
        lines.append("}\n")

        return lines
