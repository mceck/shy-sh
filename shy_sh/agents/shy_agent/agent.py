from rich import print
from shy_sh.agents.shy_agent.graph import shy_agent_graph
from shy_sh.agents.misc import get_graph_inputs, run_few_shot_examples
from shy_sh.agents.shy_agent.audio import capture_prompt
from shy_sh.utils import save_history
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
        self.examples = run_few_shot_examples()

    def _run(self, task: str):
        self.history.append(HumanMessage(content=task))
        inputs = get_graph_inputs(
            history=self.history,
            examples=self.examples,
            ask_before_execute=self.ask_before_execute,
        )

        res = shy_agent_graph.invoke(inputs)
        self.history += res["tool_history"]

    def start(self, task: str):
        if task:
            self._run(task)
        if self.interactive:
            if self.audio:
                new_task = None
                while not new_task:
                    print(f"\n🎤: ", end="")
                    new_task = capture_prompt().strip()
                    print(new_task)
            else:
                new_task = input("\n✨: ")
            while new_task.endswith("\\"):
                new_task = new_task[:-1] + "\n" + input("    ")
            save_history()
            if new_task == "exit" or new_task == "quit":
                print("\n🤖: 👋 Bye!\n")
                return

            self.start(new_task)
