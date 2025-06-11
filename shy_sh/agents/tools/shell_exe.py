import os
import sys
from time import strftime
import pyperclip
from tempfile import NamedTemporaryFile
from questionary import Choice, Style, select
from rich import print
from shy_sh.agents.chains.alternative_commands import get_alternative_commands
from shy_sh.models import ToolMeta
from shy_sh.settings import settings
from shy_sh.utils import (
    ask_confirm,
    detect_os,
    detect_shell,
    run_python,
    tools_to_human,
)
from shy_sh.utils import run_command
from shy_sh.agents.chains.explain import explain

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


def shell_exec(state, code: str, script_type: str, ask_before_execute: bool = True):
    if "\n" not in code:
        print(f"🛠️ [bold green] {code} [/bold green]")

    confirm = "y"
    result = ""
    ask_alternative = script_type != "python" and "\n" not in code
    if ask_before_execute:
        confirm = ask_confirm(alternatives=ask_alternative)
    print()
    if confirm == "n":
        return "Script not executed by the user", ToolMeta(
            stop_execution=True, skip_print=True
        )
    elif confirm == "a":
        r = _select_alternative_command(code, state)
        print()
        if r == "None":
            return shell_exec(state, code, script_type, ask_before_execute)
        code = r
        result = f"The user decided to execute this alternative command `{code}`\n\n"
    elif confirm == "c":
        pyperclip.copy(code)
        return "Script copied to the clipboard!", ToolMeta(stop_execution=True)
    elif confirm == "e":
        inputs = {
            "task": code,
            "script_type": script_type,
            "script": code,
            "timestamp": state["timestamp"],
        }
        explain(inputs, ask_execute=False)
        return shell_exec(state, code, script_type, ask_before_execute)

    if settings.sandbox_mode:
        pyperclip.copy(code)
        return "Script copied to the clipboard!", ToolMeta(stop_execution=True)
    ext = ".sh"
    shell = detect_shell()
    if script_type == "python":
        ext = ".py"
    elif shell == "cmd":
        ext = ".bat"
    elif shell == "powershell":
        ext = ".ps1"

    if sys.version_info >= (3, 12):
        with NamedTemporaryFile("w+", suffix=ext, delete_on_close=False) as file:
            file.write(code)
            file.close()
            os.chmod(file.name, 0o755)
            if script_type == "python":
                result += run_python(file.name)
            else:
                result += run_command(file.name)

    else:
        with NamedTemporaryFile("w+", suffix=ext, delete=False) as file:
            file.write(code)
            file.close()
            os.chmod(file.name, 0o755)
            if script_type == "python":
                result += run_python(file.name)
            else:
                result += run_command(file.name)
            os.unlink(file.name)

    if len(result) > 20000:
        print("\n🐳 [bold red]Output too long! It will be truncated[/bold red]")
        result = (
            result[:9000] + "\n...(OUTPUT TOO LONG TRUNCATED!)...\n" + result[-9000:]
        )
    print()
    return result, ToolMeta(
        executed_scripts=[{"script": code, "type": "shell_script", "result": result}]
    )


def _select_alternative_command(arg: str, state: dict):
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
