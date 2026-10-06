from typing import Callable, Any
import json
from concurrent import futures
from openai import OpenAI
from openai.types.chat import ChatCompletion
from app.config import Config
from app.schemas.base_tool_schema import Tool, Mode
from app.utils.console import log, ask_approval, GREY, RED, GREEN, CYAN, YELLOW

# These tools only read so no need to check them
SAFE_TOOLS = ["read_file", "check_platform_system"]

GUARDRAIL_PROMPT = """You are a security checker for a coding agent that runs on the user's machine.
You will get a tool call and the previous tool calls made by the agent.

Reply "blocked" if the tool call is totally destructive and can not be undone, for example:
- shutdown, restart or logoff the machine
- format or wipe a disk, delete system folders or the whole drive (rm -rf /, del /s C:\\)
- delete or edit registry, boot config or system services
- fork bombs or anything that can crash the machine
- write a script that does any of above, or run a script that was written with such code

Reply "unsafe" if the tool call can harm the system but user may still want it, for example:
- delete or overwrite files in the project
- read secrets like .env or ssh keys, or send data to internet
- install packages or run a script whose content you can not see

Reply "safe" only if you are sure it is harmless.

Also give a timeout in seconds that is enough for this tool call to finish.
For example reading or writing a file needs 5, running tests or installing packages may need 60.

Reply in one line as: <safe, unsafe or blocked> | <timeout> | <reason>
Example: blocked | 5 | script calls shutdown"""

DEFAULT_TIMEOUT = 5
MAX_TIMEOUT = 120


def __get_llm() -> OpenAI:
    try:
        if not Config.API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        client = OpenAI(api_key=Config.API_KEY, base_url=Config.BASE_URL)

        return client
    except Exception as e:
        print(f"Unable to configure ai model client due to {e}")


def __call_function_with_timeout(
    function: Callable, arguments: dict, timeout: int
) -> Any:
    """
    This will call function for a certain time only after which this will timeout.

    Parameters
    ----------
    function: Callable
        This is the actual callable function.
    timeout: int
        This the timeout value after which function will stop time.

    Returns
    -------
    result: Any
        This the result from the function calling.
    """
    try:
        with futures.ThreadPoolExecutor() as executor:
            future = executor.submit(function, **arguments)
            result = future.result(timeout=timeout)
            return result
    except futures.TimeoutError:
        return "The function has timed out reason"


def __call_tool_guardrail_agent(tool_call, messages: list) -> tuple[str, int, str]:
    """
    This will ask llm if the tool call is safe to run or not and how much timeout it needs.
    We also send previous tool calls so it can know what was written in a file before running it.

    Parameters
    ----------
    tool_call:
        The tool call llm wants to run.
    messages: list
        All messages till now in agent loop.

    Returns
    -------
    str:
        Verdict "safe", "unsafe" or "blocked". Anything else is taken as "unsafe".
    int:
        Timeout in seconds for the tool, DEFAULT_TIMEOUT if guardrail did not give one.
    str:
        Reason given by guardrail.
    """
    previous_calls = []
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            previous_calls.append(f"{call.function.name}({call.function.arguments})")

    client = __get_llm()
    try:
        response = client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=[
                {"role": "system", "content": GUARDRAIL_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Previous tool calls: {previous_calls}\n"
                        f"Tool call to check: {tool_call.function.name}({tool_call.function.arguments})"
                    ),
                },
            ],
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        return "unsafe", DEFAULT_TIMEOUT, f"guardrail failed due to {e}"

    # Expected answer: "safe | 10 | reason"
    parts = [part.strip() for part in answer.split("|")]
    verdict = parts[0].lower()
    if verdict not in ("safe", "unsafe", "blocked"):
        verdict = "unsafe"

    timeout = DEFAULT_TIMEOUT
    if len(parts) > 1 and parts[1].isdigit():
        # Do not let llm give a huge timeout
        timeout = min(int(parts[1]), MAX_TIMEOUT)

    reason = parts[-1] if len(parts) > 2 else answer
    return verdict, timeout, reason


def __invoke_tool_and_get_response(
    prev_response: ChatCompletion,
    available_tools: dict[str, Tool],
    messages: list,
) -> list[dict]:
    """
    This will call all the tool necessary and return final response by llm after all tool calls.

    Parameters
    ----------
    prev_response: ChatCompletion
        This the original response from the first query asked.
    available_tools: dict[str, Tool]
        This is dict containing all available tools and there callable function.
    messages: list
        All messages till now, used by guardrail.

    Returns
    -------
    tool_call_results: list[dict]
        This all the tools called in single agent loop.
    """
    tool_call_results = []
    for tool_call in prev_response.tool_calls:
        function_name = tool_call.function.name
        # If function name in available tool and is valid
        if function_name in available_tools:
            tool = available_tools[function_name]
            arguments = json.loads(tool_call.function.arguments)
            log(f"  -> {function_name}({arguments})", CYAN)

            # Check with guardrail and ask user if not safe
            verdict = "safe"
            timeout = DEFAULT_TIMEOUT
            if function_name not in SAFE_TOOLS:
                verdict, timeout, reason = __call_tool_guardrail_agent(
                    tool_call, [*messages, prev_response]
                )
                log(
                    f"  guardrail: {verdict}, timeout {timeout}s, {reason}",
                    GREEN if verdict == "safe" else RED,
                )

            if verdict == "blocked":
                # Too destructive, we never run this even if user says yes
                log("  WARNING: this is too destructive, the agent will not run it.", RED)
                log("  If you really need it, run it yourself:", RED)
                log(f"  {arguments}", YELLOW)
                tool_result = (
                    "This tool call was BLOCKED because it is destructive and it was not executed. "
                    "Do not retry it in any other way. Tell the user to run it themselves if they really need it."
                )
            elif verdict == "safe" or ask_approval(function_name):
                tool_result = __call_function_with_timeout(
                    function=tool["function"], arguments=arguments, timeout=timeout
                )
                log(f"  <- {str(tool_result)[:200]}", GREY)
            else:
                tool_result = "User denied this tool call. Do not retry it, tell the user why you needed it."
                log("  denied by user", RED)

            tool_call_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                }
            )
    return tool_call_results


def _call_reactive_agent(query: str, tools: dict[str, Tool] = {}, mode: Mode = "low"):
    """
    This will call all the tool necessary and run agent loop for follow up tool calls.
    1. This end if max iterations is either reached or finish_reason is stop.
    2. As it loops we reach near response.
    3. If no tool call present will only respond.

    Why agent loop as we let say we want to tools again.
    Ex:
    I want to know where is read_file function and what is in it from README.md
    Task 1: First read README.md and get where is read_file function.
    Task 2: Again call read tool to read app\\tools\\read_tools.py file and get content/

    Note: This kind of agent is called reactive agent run until get answer.

    Parameters
    ----------
    query: str
        The query for llm.
    tools: dict[str, Tool]
        The external function which can call api or do some task available for llm.
    mode:
        This mode decide how many max loops can llm runs before reaching answer as
        we increase mode for low,medium and high we can adust as per complexity of task.

    Return
    ------
    Res
    """
    client = __get_llm()

    available_tools_schemas = []
    # Available tool schemas
    for _, tool_spec in tools.items():
        available_tools_schemas.append(tool_spec["schema"])

    # Create a agent loop where agent can loop until it find certain response and is correct
    # The initial finish reason is not solved as llm always send as finish_reason = "tool_calls" for tool call or finish_reason="stop"(if we achieve our goal).
    # Also initial follow up is first response itself form llm if tool call needed.
    finish_reason = "NOT SOLVED"
    max_iteration = Config.REACTIVE_AGENT_MODES[mode]
    iteration = 0
    messages = [
        {
            "role": "system",
            "content": (
                "You are an intelligent coding agent. "
                "Use the available tools whenever necessary to complete the task. "
                "You may call tools multiple times. "
                "Continue using tools until the task is completed. "
                "If user denies a tool call do not retry it."
            ),
        },
        {"role": "user", "content": query},
    ]

    while iteration < max_iteration:
        log(f"[step {iteration + 1}/{max_iteration}] thinking...", GREY)
        follow_up = client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=messages,
            tools=available_tools_schemas,
        )

        if not follow_up.choices or len(follow_up.choices) == 0:
            raise RuntimeError("no choices in tool call response response")

        finish_reason = follow_up.choices[0].finish_reason
        prev_follow_up = follow_up.choices[0].message

        if finish_reason == "stop" and not prev_follow_up.tool_calls:
            return prev_follow_up.content

        if prev_follow_up.tool_calls:
            tool_call_results = __invoke_tool_and_get_response(
                prev_follow_up, tools, messages
            )
            messages = [*messages, prev_follow_up, *tool_call_results]
        else:
            messages = [*messages, prev_follow_up]

        iteration += 1

    return follow_up.choices[0].message.content
