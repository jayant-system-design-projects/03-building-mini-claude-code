import argparse
import sys
from app.handlers.reactive_agent_handlers import _call_reactive_agent
from app.tools.read_tools import READ_TOOLS
from app.tools.write_tools import WRITE_TOOLS
from app.tools.bash_tools import BASH_TOOLS
ALL_TOOLS = {**READ_TOOLS, **WRITE_TOOLS, **BASH_TOOLS}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    try:
        response = _call_reactive_agent(args.p, ALL_TOOLS)
    except Exception as e:
        response = f"Unexpected Error: {e}"

    print(response)


if __name__ == "__main__":
    main()
