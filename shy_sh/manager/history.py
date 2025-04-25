from shy_sh.agents.misc import has_tool_calls, parse_react_tool
from shy_sh.manager.sql_models import ExecutedScript, ScriptType, session
from shy_sh.manager.chat_manager import ChatManager
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from rich import print
from rich.markdown import Markdown

from shy_sh.utils import syntax, to_local


def print_chat_history():
    print("\n[bold green]Chats[/bold green]")
    with session() as db:
        chat_manager = ChatManager(db)
        chats = chat_manager.get_all_chats()
        if not chats:
            print("No chat history found.")
            return

        for chat in chats:
            print(f"[bold magenta][{chat.id}][/] - [bold green]{chat.title}[/]")
            print(
                f"  Model: {chat.meta.get('provider', '')} - {chat.meta.get('name', 'Unknown')}"
            )
            print(f"  Messages: {len(chat.messages)}")
            print(f"  Created: {to_local(chat.created_at).strftime('%Y-%m-%d %H:%M')}")


_MESSAGE_MAP = {
    "human": HumanMessage,
    "ai": AIMessage,
    "tool": ToolMessage,
}


def _serialize_messages(messages: list[dict]) -> list[BaseMessage]:
    return [
        _MESSAGE_MAP[message["type"]].model_validate(message) for message in messages
    ]


def load_chat_history(chat_id: int) -> list[BaseMessage]:
    with session() as db:
        chat_manager = ChatManager(db)
        chat = chat_manager.get_chat(chat_id)
        if not chat:
            return []
        return _serialize_messages(chat.messages)


def print_chat(chat_id: int):
    hist = load_chat_history(chat_id)
    print(Markdown("---"))
    print()
    for message in hist:
        if hasattr(message, "tool_calls") and len(message.tool_calls) > 0:  # type: ignore
            print(syntax(message.tool_calls[0]["args"].get("arg")))  # type: ignore
            print()
        else:
            try:
                rtool = parse_react_tool(message)
            except Exception:
                rtool = None
            if rtool:
                print(syntax(rtool.arg))
            else:
                avatar = "✨" if isinstance(message, HumanMessage) else "🤖"
                msg = str(message.content)
                if msg.startswith("Tool response:"):
                    msg = msg[14:].strip()
                print(Markdown(f"{avatar}: {msg}"))
            print()
    print(Markdown("---"))


def print_recent_commands(
    script_type: ScriptType | None = None,
):
    print("\n[bold green]Commands history[/bold green]")
    with session() as db:
        chat_manager = ChatManager(db)
        scripts = chat_manager.get_recent_scripts(script_type)
        for script, count, kind, created_at in reversed(scripts):
            if len(script) > 100:
                script = script[:100] + "..."
            print(
                f"\n[magenta][{kind.name}][/] {to_local(created_at).strftime('%Y-%m-%d %H:%M')}"
            )
            print(
                syntax(
                    script, lexer="python" if kind == ScriptType.PYTHON else "console"
                )
            )


def save_chat_history(
    *,
    chat_id: int | None = None,
    title: str | None = None,
    messages: list[BaseMessage] | None = None,
    meta: dict | None = None,
    executed_scripts: list[dict] | None = None,
):
    with session() as db:
        chat_manager = ChatManager(db)
        chat_manager.save_chat(
            chat_id,
            title=title,
            messages=(
                [message.model_dump() for message in messages] if messages else None
            ),
            meta=meta,
            executed_scripts=(
                [ExecutedScript(**script) for script in executed_scripts]
                if executed_scripts
                else None
            ),
        )


def truncate_chats(keep: int = 100):
    with session() as db:
        chat_manager = ChatManager(db)
        chat_manager.truncate_chats(keep)
