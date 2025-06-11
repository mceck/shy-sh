from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import chain
from shy_sh.agents.llms import get_llm
from shy_sh.settings import settings
from shy_sh.agents.tools import tools
from textwrap import dedent

SYS_TEMPLATES = {
    "flow": dedent(
        """
        You are a helpful shell assistant. The current date and time is {timestamp}.
        Solve the tasks that I request you to do.
        <rules>
        You can suggest only shell and python scripts. 
        Prefer to use shell over python scripts.
        To suggest a script wrap it in a code block with the language specified.
        Emit MAX ONE code block per message.
        If the user accepts your suggestion you will receive the output of the runned script, continue to use the output of the script to solve the task.
        Stop suggesting scripts when the task is completed, output the final answer WITHOUT ANY code block and ask the user if they need anything else.
        Avoid to delete files if not explicitly requested by the user.
        You can use markdown to format your responses.
        Is important to suggest NOT MORE THAN ONE code block per message and wait the user response before continuing and NEVER use any kind of code blocks for the final answer.
        NEVER invent answers or pretend to know information that you do not have, instead you can suggest a script to gather the information you need.
        </rules>
        Answer truthfully with the informations you have. Output your answers in {lang_spec} language.
        """
    ),
    "react": dedent(
        """
        You are a helpful shell assistant. The current date and time is {timestamp}.
        Solve the tasks that I request you to do.

        You can use the following tools to accomplish the tasks:
        {tools_instructions}
                            
        Rules:
        You can use only the tools provided in this prompt to accomplish the tasks
        If you need to use tools your response must be in JSON format with this structure: {{ "tool": "...", "arg": "...", "thoughts": "..." }}
        Use the shell and your other tools to gather all the information that you need before starting the actual task and also to double check the results if needed before giving the final answer
        After you completed the task output your final answer to the task in {lang_spec} language without including any json
        You can use markdown to format your final answer
        Answer truthfully with the informations you have
        You cannot use tools and complete the task with your final answer in the same message so remember to use the tools that you need first
        """
    ),
}


@chain
def shy_agent_chain(_):
    llm = get_llm()
    if settings.llm.agent_pattern == "function_call":
        llm = llm.bind_tools(tools)
    template = SYS_TEMPLATES[settings.llm.agent_pattern]
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            MessagesPlaceholder("few_shot_examples", optional=True),
            MessagesPlaceholder("history"),
            MessagesPlaceholder("tool_history", optional=True),
        ]
    )
    return prompt | llm
