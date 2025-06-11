from rich import print
from shy_sh.settings import settings
from shy_sh.agents.shy_agent.graph import shy_agent_graph
from shy_sh.agents.misc import get_graph_inputs, run_few_shot_examples
from shy_sh.agents.shy_agent.audio import capture_prompt
from shy_sh.manager.history import (
    print_recent_commands,
    load_chat_history,
    print_chat_history,
    save_chat_history,
    print_chat,
)
from shy_sh.utils import command_completer, save_history
from langchain_core.messages import HumanMessage


class ShyAgent:
    def __init__(
        self,
        interactive=False,
        ask_before_execute=True,
        audio=False,
    ):
        self.interactive = interactive
        self.ask_before_execute = ask_before_execute
        self.audio = audio
        self.history = []
        self.executed_scripts = []
        self.examples = run_few_shot_examples()
        self.chat_id = None

    def _run(self, task: str):
        self.history.append(HumanMessage(content=task))
        inputs = get_graph_inputs(
            history=self.history,
            examples=self.examples,
            ask_before_execute=self.ask_before_execute,
        )

        res = shy_agent_graph.invoke(inputs)
        self.history += res["tool_history"]
        self.executed_scripts += res["executed_scripts"]

    def _handle_command(self, command: str):
        if not command.startswith("/"):
            return False
        command = command[1:]
        match command:
            case "chats" | "c":
                print_chat_history()
                print("\n🤖: Here is the list of all chats!")
                return True
            case "history" | "h":
                print_recent_commands()
                print("\n🤖: Here are the most recently executed commands!")
                return True
            case "clear":
                self.history = []
                self.executed_scripts = []
                self.chat_id = None
                print("🤖: New chat started")
                return True
            case command if command.startswith("chat "):
                try:
                    print_chat(int(command[5:]))
                except ValueError:
                    print(f"🚨 [bold red]Invalid chat ID {command[5:]}[/]")
                return True
            case command if command.startswith("c "):
                try:
                    print()
                    print_chat(int(command[2:]))
                except ValueError:
                    print(f"🚨 [bold red]Invalid chat ID {command[2:]}[/]")
                return True
            case command if command.startswith("load "):
                try:
                    chat_id = int(command[5:])
                    self.history = load_chat_history(chat_id)
                    if self.history:
                        self.chat_id = chat_id
                        print(f"🤖: Loaded history for chat ID {chat_id}")
                    else:
                        print(f"🤖: No history found for chat ID {chat_id}")
                except ValueError:
                    print(f"🚨 [bold red]Invalid chat ID {command[5:]}[/]")
                return True
        return False

    def _load_autocomplete(self):
        try:
            import readline

            readline.set_completer(command_completer)
        except Exception:
            pass

    def _dispose_autocomplete(self):
        try:
            import readline

            readline.set_completer(lambda *args: None)
        except Exception:
            pass

    def start(self, task: str):
        if task:
            self._run(task)
            if self.history:
                save_chat_history(
                    chat_id=self.chat_id,
                    title=task if not self.chat_id else None,
                    messages=self.history,
                    executed_scripts=self.executed_scripts,
                    meta=settings.llm.model_dump(exclude={"api_key"}),
                )
        if self.interactive:
            if self.audio:
                new_task = None
                while not new_task:
                    print(f"\n🎤: ", end="")
                    new_task = capture_prompt().strip()
                    print(new_task)
            else:
                self._load_autocomplete()
                new_task = input("\n✨: ")
                self._dispose_autocomplete()
            while new_task.endswith("\\"):
                new_task = new_task[:-1] + "\n" + input("  > ")
            save_history()

            if new_task == "exit" or new_task == "quit" or new_task == "q":
                print("\n🤖: 👋 Bye!\n")
                return
            if new_task.startswith("/"):
                r = self._handle_command(new_task)
                if r:
                    new_task = ""

            self.start(new_task)
