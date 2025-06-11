import re
import json
from time import strftime
from uuid import uuid4
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from shy_sh.settings import settings
from shy_sh.utils import detect_shell, detect_os, run_shell
from shy_sh.agents.tools import tools
from shy_sh.models import ToolRequest


def get_graph_inputs(
    history: list,
    examples: list,
    ask_before_execute: bool,
):
    return {
        "history": history,
        "timestamp": strftime("%Y-%m-%d %H:%M %Z"),
        "ask_before_execute": ask_before_execute,
        "lang_spec": settings.language or "",
        "few_shot_examples": examples,
        "tools_instructions": _format_tools(),
    }


def parse_react_tool(message):
    start_idx = message.content.index("{")
    if start_idx < 0:
        raise ValueError("No tool call found")
    end_idx = start_idx + 1
    open_brackets = 1
    while open_brackets > 0 and end_idx < len(message.content):
        if message.content[end_idx] == "{":
            open_brackets += 1
        elif message.content[end_idx] == "}":
            open_brackets -= 1
        end_idx += 1
    maybe_tool = message.content[start_idx:end_idx]
    try:
        return ToolRequest.model_validate_json(maybe_tool)
    except Exception:
        try:
            maybe_tool = message.content[start_idx : message.content.rindex("}") + 1]
            return ToolRequest.model_validate_json(maybe_tool)
        except Exception:
            maybe_tool = re.sub(r"\\(?!\\)", r"\\\\", maybe_tool)
            return ToolRequest.model_validate_json(maybe_tool)


def has_tool_calls(message):
    if settings.llm.agent_pattern == "function_call":
        if bool(getattr(message, "tool_calls", None)):
            return True
    elif settings.llm.agent_pattern == "flow":
        if (message.content or "").count("```") >= 2:
            return True
    elif settings.llm.agent_pattern == "react":
        try:
            parse_react_tool(message)
            return True
        except Exception:
            pass
    return False


def run_flow_few_shot_examples():
    shell = detect_shell()
    os = detect_os()
    pwd_cmd = "echo %cd%" if shell in ["powershell", "cmd"] else "pwd"
    return [
        HumanMessage(
            content=f"You are on {os} system using {shell} as shell. To begin check the current directory and if you are in a git repository."
        ),
        AIMessage(
            content=f"Ok, to check the shell, I will run:\n```{shell}\n{ pwd_cmd}\n```\nthis command will return the current working directory."
        ),
        HumanMessage(content=run_shell(pwd_cmd)),
        AIMessage(
            content=f"Let's see if we are in a git repository\n```{shell}\ngit rev-parse --abbrev-ref HEAD\n```"
        ),
        HumanMessage(content=run_shell("git rev-parse --abbrev-ref HEAD")),
        AIMessage(content="Well done! 👍\nDo you need anything else?"),
    ]


def run_few_shot_examples():
    if settings.llm.agent_pattern == "flow":
        return run_flow_few_shot_examples()
    shell = detect_shell()
    os = detect_os()
    actions = [
        {
            "tool": "shell",
            "arg": "echo test" if shell in ["powershell", "cmd"] else "echo $SHELL",
            "thoughts": "I'm checking the current shell",
        },
        {
            "tool": "shell",
            "arg": "echo %cd%" if shell in ["powershell", "cmd"] else "pwd",
            "thoughts": "I'm checking the current working directory",
        },
        {
            "tool": "shell",
            "arg": "git rev-parse --abbrev-ref HEAD",
            "thoughts": "I'm checking if it's a git repository",
        },
    ]
    result = []
    result.append(
        HumanMessage(
            content=f"You are on {os} system using {shell} as shell. Check your tools to get started."
        )
    )
    for action in actions:
        uid = str(uuid4())
        ai_message, response = _run_example(action, uid)
        result.append(ai_message)
        if settings.llm.agent_pattern == "react":
            result.append(HumanMessage(content=f"Tool response:\n{response}"))
        elif settings.llm.agent_pattern == "function_call":
            result.append(ToolMessage(content=response, tool_call_id=uid))
    result.append(AIMessage(content="All set! 👍"))
    return result


def _run_example(action, uid):
    ai_message = AIMessage(
        content="",
        tool_calls=[
            {
                "id": uid,
                "type": "tool_call",
                "name": action["tool"],
                "args": {"arg": action["arg"]},
            }
        ],
    )
    if settings.llm.agent_pattern == "react":
        ai_message.content = json.dumps(action)
        ai_message.tool_calls = []
    return ai_message, run_shell(action["arg"])


def _format_tools():
    if settings.llm.agent_pattern == "function_call":
        return None
    return "\n".join(map(lambda tool: f'- "{tool.name}": {tool.description}', tools))
