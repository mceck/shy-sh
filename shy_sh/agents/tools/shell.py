import pyperclip
from typing import Annotated
from rich import print
from langgraph.prebuilt import InjectedState
from langchain.tools import tool
from questionary import select, Style, Choice
from shy_sh.models import State, ToolMeta
from shy_sh.utils import (
    ask_confirm,
    run_command,
    tools_to_human,
    detect_shell,
    detect_os,
)
from shy_sh.agents.chains.explain import explain
from shy_sh.agents.chains.alternative_commands import get_alternative_commands
from shy_sh.settings import settings

_text_style = {
    "qmark": "",
    "style": Style.from_dict(
        {
            "selected": "fg:ansigreen noreverse bold",
            "question": "fg:darkorange nobold",
            "highlighted": "fg:ansigreen bold",
            "text": "fg:ansigreen bold",
            "answer": "fg:ansigreen bold",
            "instruction": "fg:ansigreen",
        }
    ),
}

_select_style = {
    "pointer": "►",
    "instruction": " ",
    **_text_style,
}


@tool(response_format="content_and_artifact")
def shell(arg: str, state: Annotated[State, InjectedState]):
    """to execute a shell command in the terminal, useful for every task that requires to interact with the current system or local files, do not pass multiple lines commands, avoid to install new packages if not explicitly requested"""
    print(f"🛠️ [bold green] {arg} [/bold green]")
    result = ""
    confirm = "y"
    if state["ask_before_execute"]:
        confirm = ask_confirm(alternatives=True)
    print()
    if confirm == "n":
        return "Command interrupted by the user", ToolMeta(
            stop_execution=True, skip_print=True
        )
    elif confirm == "c":
        pyperclip.copy(arg)
        return "Command copied to the clipboard!", ToolMeta(stop_execution=True)
    elif confirm == "a":
        r = _select_alternative_command(arg, state)
        print()
        if r == "None":
            return "Command interrupted by the user", ToolMeta(
                stop_execution=True, skip_print=True
            )
        if settings.sandbox_mode:
            pyperclip.copy(r)
            return "Command copied to the clipboard!", ToolMeta(stop_execution=True)
        arg = r
        result += f"The user decided to execute this alternative command `{arg}`\n\n"
    elif confirm == "e":
        inputs = {
            "task": state["history"][-1].content,
            "script_type": "shell command",
            "script": arg,
            "timestamp": state["timestamp"],
        }
        ret = explain(inputs, ask_alternative=True)
        if ret == "alternative":
            r = _select_alternative_command(arg, state)
            print()
            if r == "None":
                return "Command interrupted by the user", ToolMeta(
                    stop_execution=True, skip_print=True
                )
            arg = r
            result += (
                f"The user decided to execute this alternative command `{arg}`\n\n"
            )
        elif ret:
            return ret
    output = run_command(arg)
    result += output

    if len(result) > 20000:
        print("\n🐳 [bold red]Output too long! It will be truncated[/bold red]")
        result = (
            result[:9000] + "\n...(OUTPUT TOO LONG TRUNCATED!)...\n" + result[-9000:]
        )
    return result, ToolMeta(
        executed_scripts=[{"script": arg, "type": "shell", "result": output}]
    )


def _select_alternative_command(arg, state):
    inputs = {
        "timestamp": state["timestamp"],
        "shell": detect_shell(),
        "system": detect_os(),
        "history": tools_to_human(state["history"] + state["tool_history"]),
        "cmd": arg,
    }
    cmds = get_alternative_commands(inputs)
    r = select(
        (
            "Pick the command to copy to the clipboard"
            if settings.sandbox_mode
            else "Pick the command to execute"
        ),
        choices=[
            Choice([("fg:ansired bold", "Cancel")], "None"),
            Choice(
                [
                    ("fg:ansiyellow bold", arg),
                    ("fg:gray", " # Original command"),
                ],
                arg,
            ),
            *[
                Choice(
                    [("fg:ansigreen bold", c[1]), ("fg:gray", " " + c[0])],
                    c[1],
                )
                for c in cmds
            ],
        ],
        **_select_style,
    ).unsafe_ask()

    return r
