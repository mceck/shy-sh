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
from shy_sh.utils import ask_confirm, tools_to_human, syntax, run_python, parse_code
from shy_sh.agents.chains.python_expert import pyexpert_chain
from shy_sh.agents.chains.explain import explain


@tool(response_format="content_and_artifact")
def python_expert(arg: str, state: Annotated[State, InjectedState]):
    """to delegate the task to a python expert that can write and execute python code, use only if you cant resolve the task with shell, just explain what do you want to achieve in a short sentence in the arg without including any python code"""
    print(f"🐍 [bold yellow]Generating python script...[/bold yellow]\n")
    inputs = {
        "timestamp": state["timestamp"],
        "history": tools_to_human(state["history"] + state["tool_history"]),
        "input": arg,
    }
    code = ""
    with Live(vertical_overflow="visible") as live:
        for chunk in pyexpert_chain.stream(inputs):
            code += chunk  # type: ignore
            live.update(syntax(code, "python"))
        code = parse_code(code)
        live.update(syntax(code.strip(), "python"))

    confirm = "y"
    if state["ask_before_execute"]:
        confirm = ask_confirm()
    print()
    if confirm == "n":
        return "Command canceled by user", ToolMeta(
            stop_execution=True, skip_print=True
        )
    elif confirm == "c":
        pyperclip.copy(code)
        return "Script copied to the clipboard!", ToolMeta(stop_execution=True)
    elif confirm == "e":
        inputs = {
            "task": arg,
            "script_type": "python script",
            "script": code,
            "timestamp": state["timestamp"],
        }
        ret = explain(inputs)
        if ret:
            return ret

    if sys.version_info >= (3, 12):
        with NamedTemporaryFile("w+", suffix=".py", delete_on_close=False) as file:
            file.write(code)
            file.close()
            os.chmod(file.name, 0o755)
            result = run_python(file.name)

            if len(result) > 20000:
                print("\n🐳 [bold red]Output too long! It will be truncated[/bold red]")
                result = (
                    result[:9000]
                    + "\n...(OUTPUT TOO LONG TRUNCATED!)...\n"
                    + result[-9000:]
                )

    else:
        with NamedTemporaryFile("w+", suffix=".py", delete=False) as file:
            file.write(code)
            file.close()
            os.chmod(file.name, 0o755)
            result = run_python(file.name)

            if len(result) > 20000:
                print("\n🐳 [bold red]Output too long! It will be truncated[/bold red]")
                result = (
                    result[:9000]
                    + "\n...(OUTPUT TOO LONG TRUNCATED!)...\n"
                    + result[-9000:]
                )
            os.unlink(file.name)

    ret = f"\nScript executed:\n```python\n{code.strip()}\n```\n\nOutput:\n{result}"
    if len(ret) > 20000:
        ret = f"Output:\n{result}"
    return (
        ret,
        ToolMeta(
            executed_scripts=[{"script": code, "type": "python", "result": result}]
        ),
    )
