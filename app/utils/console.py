import sys

GREY = "\033[90m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def log(text: str, color: str = RESET):
    """
    This will print the text in given color so we can see what agent is doing.
    Logs go to stderr so stdout only has the final answer.

    Parameters
    ----------
    text: str
        The text to print.
    color: str
        The ansi color code from above constants, default is RESET (no color).

    Returns
    -------
    None
    """
    print(f"{color}{text}{RESET}", file=sys.stderr, flush=True)


def ask_approval(tool_name: str) -> bool:
    """
    This will ask user if the tool call can run or not.
    If no input is available (like in CI or piped run) it will be taken as No.

    Parameters
    ----------
    tool_name: str
        The name of tool which needs approval.

    Returns
    -------
    bool:
        True if user typed y or yes else False
    """
    log(f"  Allow {tool_name} to run? [y/N]: ", YELLOW)
    try:
        return input().strip().lower() in ("y", "yes")
    except EOFError:
        return False
