import json
from time import strftime
from uuid import uuid4
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from shy_sh.settings import settings
from shy_sh.utils import detect_shell, detect_os, run_shell
from shy_sh.agents.tools import tools
from shy_sh.models import ToolRequest


def get_graph_inputs(
    task: str,
    history: list,
    examples: list,
    ask_before_execute: bool,
):
    return {
        "input": task,
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
        maybe_tool = message.content[start_idx : message.content.rindex("}") + 1]
        return ToolRequest.model_validate_json(maybe_tool)


def has_tool_calls(message):
    if settings.llm.agent_pattern == "function_call":
        return bool(getattr(message, "tool_calls", None))
    elif settings.llm.agent_pattern == "react":
        try:
            parse_react_tool(message)
            return True
        except Exception:
            pass
    return False


def run_few_shot_examples():
    shell = detect_shell()
    os = detect_os()
    actions = [
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
        {
            "tool": "shell",
            "arg": "history",
            "thoughts": "I'm checking the last commands runned in the shell to get some context",
        },
    ]
    result = []
    result.append(
        HumanMessage(
            content=f"You are on {os} system using {shell} as shell. Check your tools"
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
    result.append(AIMessage(content="Ok"))
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