import os
from app.schemas.base_tool_schema import ToolBase, Function, Parameters, Properties


def __read_file(file_path: str) -> str:
    """
    This will read file and return content in file.

    Parameters
    ----------
    file_path: str
        This is file path for file to access and get content.

    Returns
    -------
    content: str
        Content in file.

    Raises
    ------
    FileNotFoundError:
        If the file is not found on system.
    PermissionError:
        If we do no have permission to open file.
    """
    try:
        with open(os.path.abspath(file_path), "r", encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        return f"File named {file_path} does not exist."

    except PermissionError as p:
        return f"File named {file_path} cannot be read due to permission restrictions."


READ_TOOLS = {
    "read_file": {
        "schema": ToolBase(
            function=Function(
                name="read_file",
                description="Read and return the contents of a file or file at any path if not give use current directory.",
                parameters=Parameters(
                    properties={
                        "file_path": Properties(
                            type="string",
                            description="The path to the file to read.",
                        )
                    }
                ),
                required=["file_path"],
            )
        ).model_dump(mode="python", by_alias=True),
        "function": __read_file,
    },
}
