import typer
from typing import Optional, Annotated
from importlib.metadata import version
from shy_sh.agents.shy_agent.agent import ShyAgent
from shy_sh.manager.history import truncate_chats
from shy_sh.settings import settings, configure_yaml
from shy_sh.agents.chains.explain import explain as do_explain
from shy_sh.utils import load_history
from rich import print
from time import strftime


def exec(
    prompt: Annotated[Optional[list[str]], typer.Argument(allow_dash=False)] = None,
    oneshot: Annotated[
        Optional[bool],
        typer.Option(
            "-o",
            help="One shot mode",
        ),
    ] = False,
    no_ask: Annotated[
        Optional[bool],
        typer.Option(
            "-x",
            help="Do not ask for confirmation before executing scripts",
        ),
    ] = False,
    explain: Annotated[
        Optional[bool],
        typer.Option(
            "-e",
            help="Explain the given shell command",
        ),
    ] = False,
    audio: Annotated[
        Optional[bool],
        typer.Option(
            "-a",
            help="Interactive mode with audio input",
        ),
    ] = False,
    configure: Annotated[
        Optional[bool], typer.Option("--configure", help="Configure LLM")
    ] = False,
    display_version: Annotated[
        Optional[bool], typer.Option("--version", help="Show version")
    ] = False,
):
    if display_version:
        print(f"Version: {version(__package__ or 'shy-sh')}")
        return
    if configure:
        configure_yaml()
        return
    task = " ".join(prompt or [])
    print(f"[bold italic dark_orange]{settings.llm.provider} - {settings.llm.name}[/]")
    if explain:
        if not task:
            print("🚨 [bold red]No command provided[/]")
        do_explain(
            {
                "task": "explain this shell command",
                "script_type": "shell command",
                "script": task,
                "script_type": "shell command",
                "timestamp": strftime("%Y-%m-%d %H:%M:%S"),
            },
            ask_execute=False,
        )
        return
    interactive = not oneshot
    if task:
        print(f"\n✨: {task}\n")
    try:
        ShyAgent(
            interactive=interactive,
            ask_before_execute=not no_ask,
            audio=bool(audio),
        ).start(task)
    except Exception as e:
        print(f"🚨 [bold red]{e}[/bold red]")


def main():
    try:
        truncate_chats(1000)
        import readline

        readline.set_history_length(100)
        readline.set_completer_delims(" \t\n")
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set show-all-if-unmodified on")
    except Exception:
        pass
    load_history()
    typer.run(exec)


if __name__ == "__main__":
    main()
