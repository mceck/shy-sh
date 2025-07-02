import typer
from typing import Optional, Annotated
from importlib.metadata import version
from shy_sh.agents.shy_agent.agent import ShyAgent
from shy_sh.manager.history import truncate_chats
from shy_sh.settings import (
    delete_settings_file,
    list_settings_files,
    pull_settings_file,
    push_settings_file,
    settings,
    configure_yaml,
)
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
        Optional[bool], typer.Option("--configure", "-c", help="Configure LLM")
    ] = False,
    push_config: Annotated[
        Optional[str], typer.Option("--push-config", "-s", help="Backup current config")
    ] = None,
    pull_config: Annotated[
        Optional[str],
        typer.Option("--pull-config", "-p", help="Restore config from backup"),
    ] = None,
    list_configs: Annotated[
        Optional[bool],
        typer.Option("--list-configs", "-l", help="List available configs"),
    ] = False,
    del_config: Annotated[
        Optional[str], typer.Option("--del-config", "-d", help="Delete a config")
    ] = None,
    display_version: Annotated[
        Optional[bool], typer.Option("--version", "-v", help="Show version")
    ] = False,
):
    if display_version:
        print(f"Version: {version(__package__ or 'shy-sh')}")
        return
    if configure:
        configure_yaml()
        return
    if push_config:
        push_settings_file(push_config)
        return
    if pull_config:
        pull_settings_file(pull_config)
        return
    if list_configs:
        list_settings_files()
        return
    if del_config:
        delete_settings_file(del_config)
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
