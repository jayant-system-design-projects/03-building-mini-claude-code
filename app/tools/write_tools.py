from pathlib import Path
from app.schemas.base_tool_schema import ToolBase, Function, Parameters, Properties


def __write_file(file_path: str, content: str) -> str:
    """
    This will write content in file if exist else create one and write.

    Parameters
    ----------
    file_path: str
        This is file path for file to access and get content.
    content: str
        This is content to be written in file.

    Returns
    -------
    str:
        Return message as if file created or else not created.

    Raises
    ------
    FileNotFoundError:
        If the file is not found on system.
    PermissionError:
        If we do no have permission to open file.
    """
    try:
        with Path(file_path).open("w", encoding="utf-8") as f:
            f.write(content)
        return f"File {file_path} is create successfully and content is written in it."
    except PermissionError as p:
        return f"File named {file_path} cannot be read due to permission restrictions."


WRITE_TOOLS = {
    "write_file": {
        "schema": ToolBase(
            function=Function(
                name="write_file",
                description="Write content to a file if exist else create one and write",
                parameters=Parameters(
                    properties={
                        "file_path": Properties(
                            type="string",
                            description="The path of the file to write to if not provided use current directory",
                        ),
                        "content": Properties(
                            type="string",
                            description="The content to write to the file",
                        ),
                    }
                ),
                required=["file_path", "content"],
            )
        ).model_dump(mode="python", by_alias=True),
        "function": __write_file,
    },
}
