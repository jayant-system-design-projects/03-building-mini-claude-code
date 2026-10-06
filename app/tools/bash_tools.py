import re
import subprocess
import platform
from app.schemas.base_tool_schema import ToolBase, Function, Parameters, Properties


def __check_if_command_is_safe(system: str, command: str) -> tuple[str, bool]:
    """
    Checks if a shell command is safe to run on the given operating system.

    Parameters
    ----------
    command: str
        This is command which need execution.
    system: str
        The system/OS name, e.g. 'Linux', 'Windows' or 'Java'.

    Returns
    -------
    str:
        "safe" if no dangerous patterns are detected, or an error message explaining the risk if it fails the security check.
    bool:
        True if safe else False
    """
    # Normalize command to lowercase for consistent checking
    cmd_lower = command.lower().strip()

    # 1. Cross-Platform Shell Injection Risks
    # Chaining operators allow attackers to append malicious commands
    injection_operators = [";", "&&", "||", "|", "`", "$(", "\n"]
    for op in injection_operators:
        if op in command:  # Check original text to protect specific symbols
            return (
                f"Unsafe: Contains chaining or shell injection operator '{op}'",
                False,
            )

    # 2. OS-Specific Dangerous Keywords & Path Truncations
    if system == "Windows":
        # Block directory deletions, registry edits, formatting, and forced shutdowns
        windows_blacklist = [
            r"\brmdir\s+/s",
            r"\bdel\s+/f",
            r"\bformat\b",
            r"\brd\s+/s",
            r"\breg\s+delete",
            r"\bshutdown\s+/s",
            r"\bpowershell\b",
            r"\bcmd\b",
        ]
        for pattern in windows_blacklist:
            if re.search(pattern, cmd_lower):
                return (
                    "Unsafe: Detected dangerous Windows command or administrative tool modification.",
                    False,
                )

    elif system in ["Linux", "Darwin"]:  # Linux and macOS (Darwin) share Unix roots
        # Block root directory deletions, fork bombs, and raw device overwrites
        unix_blacklist = [
            r"rm\s+-rf\s+/",
            r"rm\s+-rf\s+\*",
            r"dd\s+if=",
            r":\(\){.*};:",
            r"chmod\s+-r\s+777\s+/",
            r"> /dev/sda",
            r"mkfs",
        ]
        for pattern in unix_blacklist:
            if re.search(pattern, cmd_lower):
                return (
                    f"Unsafe: Detected dangerous {system} root command or system file wipe.",
                    False,
                )

    else:
        return (
            f"Error: Unknown or unsupported operating system system '{system}'",
            False,
        )

    return "safe", True


def __check_platform_system() -> str:
    """
    This will return system of platform be windows,linux or macos.

    Parameters
    ----------
    None

    Returns
    -------
    platform: str
        The system/OS name, e.g. 'Linux', 'Windows' or 'Java'.
    """
    return platform.system()


def __bash_command_executor(command: str, system: str) -> dict | str:
    """
    This will write content in file if exist else create one and write.

    Parameters
    ----------
    command: str
        This is command which need execution.
    system: str
        The system/OS name, e.g. 'Linux', 'Windows' or 'Java'.

    Returns
    -------
    dict | str:
        Return message as if command is malicious else return response of execution.

    Raises
    ------
    FileNotFoundError:
        If the file is not found on system.
    PermissionError:
        If we do no have permission to open file.
    """
    if system == "Windows":
        shell = "cmd.exe"
    else:
        shell = "/bin/bash"

    message, is_safe = __check_if_command_is_safe(system, command)

    if not is_safe:
        return message

    result = subprocess.run(
        command,
        shell=True,
        executable=shell if system != "Windows" else None,
        capture_output=True,
        text=True,
    )

    return {
        "result": result.stdout,
        "error": result.stderr,
        "return_code": result.returncode,
    }


BASH_TOOLS = {
    "check_platform_system": {
        "schema": ToolBase(
            function=Function(
                name="check_platform_system",
                description="This tool let you know os is windows,linux or mac to run bash commands.",
                parameters=Parameters(),
                required=[],
            )
        ).model_dump(mode="python", by_alias=True),
        "function": __check_platform_system,
    },
    "bash_tool": {
        "schema": ToolBase(
            function=Function(
                name="bash_tool",
                description="Execute a shell command for all kind of tasks also can checks if command is malicious before execution.",
                parameters=Parameters(
                    properties={
                        "command": Properties(
                            type="string",
                            description="The command to execute",
                        ),
                        "system": Properties(
                            type="string",
                            description="The system/OS name, e.g. 'Linux', 'Windows' or 'Java'.",
                        ),
                    }
                ),
                required=["command", "system"],
            )
        ).model_dump(mode="python", by_alias=True),
        "function": __bash_command_executor,
    },
}
