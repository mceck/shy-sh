from uuid import uuid4
from langchain_core.messages import ToolMessage, HumanMessage
from rich import print
from shy_sh.agents.tools.shell_exe import shell_exec
from shy_sh.models import State
from shy_sh.agents.tools import tools_by_name
from shy_sh.settings import settings
from shy_sh.agents.misc import parse_react_tool


def tools_handler(state: State):
    last_message = state["tool_history"][-1]

    tool_answers = []
    executed_scripts = []
    if settings.llm.agent_pattern == "flow":
        # check message scripts
        if "```" in last_message.content:
            script = last_message.content.split("```")[1].strip()
            script_type = script.split("\n", 1)[0].strip().split(" ")[0].strip()
            script = script.replace(script_type, "", 1).strip()
            if not script:
                return {}
            try:
                print()
                result, art = shell_exec(
                    state,
                    script,
                    script_type,
                    ask_before_execute=state["ask_before_execute"],
                )
                message = HumanMessage(content=result)
                message.artifact = art
                executed_scripts += [
                    {
                        "script": script,
                        "type": script_type,
                        "result": message.content,
                    }
                ]
            except Exception as e:
                print(f"[bold red]🚨 Execution error: {e}[/bold red]")
                message = HumanMessage(f"Execution error: {e}")
            tool_answers.append(message)
        return {"tool_history": tool_answers, "executed_scripts": executed_scripts}

    t_calls = _get_tool_calls(last_message)
    for t_call in t_calls:
        try:
            t = tools_by_name[t_call["name"]]
            message = t.invoke(
                {
                    **t_call,
                    "args": {"state": state, **t_call["args"]},
                }
            )
        except Exception as e:
            print(f"[bold red]🚨 Tool error: {e}[/bold red]")
            message = ToolMessage(f"Tool error: {e}", tool_call_id=t_call["id"])

        if settings.llm.agent_pattern == "react":
            m = HumanMessage(content=f"Tool response:\n{message.content}")
            m.artifact = getattr(message, "artifact", None)
            message = m
        tool_answers.append(message)
        if hasattr(message, "artifact") and message.artifact.executed_scripts:
            executed_scripts += message.artifact.executed_scripts
    return {"tool_history": tool_answers, "executed_scripts": executed_scripts}


def _get_react_tool_calls(message):
    react_tool = parse_react_tool(message)
    return [
        {
            "name": react_tool.tool,
            "args": {"arg": react_tool.arg},
            "id": uuid4().hex,
            "type": "tool_call",
        }
    ]


def _get_function_call_tool_calls(message):
    return message.tool_calls


def _get_tool_calls(message):
    match (settings.llm.agent_pattern):
        case "react":
            return _get_react_tool_calls(message)
        case "function_call":
            return _get_function_call_tool_calls(message)
        case _:
            return []
