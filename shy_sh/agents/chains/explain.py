import pyperclip
from langchain_core.runnables import chain
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
from shy_sh.agents.llms import get_llm
from shy_sh.utils import ask_confirm
from shy_sh.models import ToolMeta
from shy_sh.settings import settings
from textwrap import dedent
from rich.live import Live
from rich.markdown import Markdown
from rich import print


msg_template = dedent(
    """
    The given task was {task}.
    Explain this {script_type} and why it should solve the task{lang_spec}.
    Be concise and please limit your explanation to the provided {script_type} and avoid suggesting alternative solutions or directly referencing the given task.
    You can use markdown formatting to enhance the explanation.
    ```
    {script}
    ```
    """
)


@chain
def explain_chain(_):
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a shell expert. The current date and time is {timestamp}.",
            ),
            ("human", msg_template),
        ]
    )
    return prompt | llm | StrOutputParser()


def explain(inputs, ask_execute=True, ask_alternative=False):
    with Live(vertical_overflow="visible") as live:
        text = "🤖:\n"
        for chunk in explain_chain.stream(
            {
                **inputs,
                "lang_spec": (
                    f" in {settings.language} language" if settings.language else ""
                ),
            }
        ):
            text += chunk
            live.update(Markdown(text))
    print()

    if not ask_execute:
        return
    print(f"🛠️ [bold green] {inputs['script']} [/bold green]")
    confirm = ask_confirm(explain=False, alternatives=ask_alternative)
    if confirm == "n":
        return "Command canceled by user", ToolMeta(
            stop_execution=True, skip_print=True
        )
    elif confirm == "c":
        pyperclip.copy(inputs["script"])
        return "Script copied to the clipboard!", ToolMeta(stop_execution=True)
    elif confirm == "a":
        return "alternative"
