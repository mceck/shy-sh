import os
import sys
import pyperclip
from typing import Annotated
from tempfile import NamedTemporaryFile
from rich import print
from rich.live import Live
from langgraph.prebuilt import InjectedState
from langchain.tools import tool
from shy_sh.models import State, ToolMeta
from shy_sh.utils import ask_confirm, detect_shell, detect_os, parse_code
from shy_sh.agents.chains.shell_expert import shexpert_chain
from shy_sh.utils import run_command, tools_to_human, syntax
from shy_sh.agents.chains.explain import explain


@tool(response_format="content_and_artifact")
def shell_expert(arg: str, state: Annotated[State, InjectedState]):
    """to delegate the task to a shell expert that can write and execute long and complex shell scripts, use only if you cant resolve the task with a simple shell command, just explain what do you want to achieve in a short sentence in the arg without including any shell code"""
    print(f"💻 [bold dark_green]Generating shell script...[/bold dark_green]\n")
    shell = detect_shell()
    system = detect_os()
    inputs = {
        "input": arg,
        "system": system,
        "shell": shell,
        "timestamp": state["timestamp"],
        "history": tools_to_human(state["history"] + state["tool_history"]),
    }
    code = ""
    with Live(vertical_overflow="visible") as live:
        for chunk in shexpert_chain.stream(inputs):
            code += chunk  # type: ignore
            live.update(syntax(code))

        code = parse_code(code)
        live.update(syntax(code.strip()))

    confirm = "y"
    if state["ask_before_execute"]:
        confirm = ask_confirm()
    print()
    if confirm == "n":
        return "Script interrupted by the user", ToolMeta(
            stop_execution=True, skip_print=True
        )
    elif confirm == "c":
        pyperclip.copy(code)
        return "Script copied to the clipboard!", ToolMeta(stop_execution=True)
    elif confirm == "e":
        inputs = {
            "task": arg,
            "script_type": "shell script",
            "script": code,
            "timestamp": state["timestamp"],
        }
        ret = explain(inputs)
        if ret:
            return ret

    ext = ".sh"
    if shell == "cmd":
        ext = ".bat"
    elif shell == "powershell":
        ext = ".ps1"

    if sys.version_info >= (3, 12):
        with NamedTemporaryFile("w+", suffix=ext, delete_on_close=False) as file:
            file.write(code)
            file.close()
            os.chmod(file.name, 0o755)
            result = run_command(file.name)

            if len(result) > 20000:
                print("\n🐳 [bold red]Output too long! It will be truncated[/bold red]")
                result = (
                    result[:9000]
                    + "\n...(OUTPUT TOO LONG TRUNCATED!)...\n"
                    + result[-9000:]
                )

    else:
        with NamedTemporaryFile("w+", suffix=ext, delete=False) as file:
            file.write(code)
            file.close()
            os.chmod(file.name, 0o755)
            result = run_command(file.name)

            if len(result) > 20000:
                print("\n🐳 [bold red]Output too long! It will be truncated[/bold red]")
                result = (
                    result[:9000]
                    + "\n...(OUTPUT TOO LONG TRUNCATED!)...\n"
                    + result[-9000:]
                )
            os.unlink(file.name)
    print()
    ret = f"Script executed:\n{code}\n\nOutput:\n{result}"
    if len(ret) > 20000:
        ret = f"Output:\n{result}"
    return ret, ToolMeta(
        executed_scripts=[{"script": code, "type": "shell_script", "result": result}]
    )
