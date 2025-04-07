import yaml
from tests.utils import mock_llm


def test_version(exec):
    result = exec("--version")
    assert result.exit_code == 0
    assert result.stdout.startswith("Version: ")


def test_question(exec, mocker):
    with mock_llm(mocker):
        result = exec("-o how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "🤖: test" in result.stdout


def test_interactive_question(exec, mocker):
    with mock_llm(mocker, ["fine thanks"]):
        result = exec("how are you", input="exit\n")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "🤖: fine thanks" in result.stdout
        assert "👋 Bye!" in result.stdout


def test_use_shell_tool(exec, mocker):
    confirm = mocker.patch("shy_sh.agents.tools.shell.ask_confirm", return_value="y")
    with mock_llm(
        mocker,
        [
            '{"tool": "shell", "arg": "echo fine thanks", "thoughts": "test"}',
            "fine thanks",
        ],
    ):
        result = exec("-o how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert confirm.call_count == 1
        assert "🛠️  echo fine thanks" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_shell_tool_with_alternatives(exec, mocker):
    confirm = mocker.patch("shy_sh.agents.tools.shell.ask_confirm", return_value="a")
    select = mocker.patch(
        "shy_sh.agents.tools.shell._select_alternative_command",
        return_value="echo fine thanks",
    )
    with mock_llm(
        mocker,
        [
            '{"tool": "shell", "arg": "echo fine thanks", "thoughts": "test"}',
            "fine thanks",
        ],
    ):
        result = exec("-o how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert confirm.call_count == 1
        assert select.call_count == 1
        assert "🛠️  echo fine thanks" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_shell_tool_with_explain(exec, mocker):
    confirm = mocker.patch(
        "shy_sh.agents.tools.shell.ask_confirm", side_effect=["e", "y"]
    )
    with mock_llm(
        mocker,
        [
            '{"tool": "shell", "arg": "echo fine thanks", "thoughts": "test"}',
            "fine thanks",
        ],
    ):
        result = exec("-o how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        # assert confirm.call_count == 2 FIXME
        assert "🛠️  echo fine thanks" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_shell_tool_no_confirmation(exec, mocker):
    with mock_llm(
        mocker,
        [
            '{"tool": "shell", "arg": "echo fine thanks", "thoughts": "test"}',
            "fine thanks",
        ],
    ):
        result = exec("-o -x how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert (
            "Do you want to execute this command? [Yes/no/copy/explain]"
            not in result.stdout
        )
        assert "🛠️  echo fine thanks" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_shell_expert_tool(exec, mocker):
    confirm = mocker.patch(
        "shy_sh.agents.tools.shell_expert.ask_confirm", return_value="y"
    )
    with mock_llm(
        mocker,
        [
            '{"tool": "shell_expert", "arg": "say how are you", "thoughts": "test"}',
            "```sh\necho fine thanks\n```",
            "fine thanks",
        ],
    ):
        result = exec("-o how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "💻 Generating shell script..." in result.stdout
        assert confirm.call_count == 1
        assert "echo fine thanks" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_shell_expert_tool_no_confirmation(exec, mocker):
    confirm = mocker.patch(
        "shy_sh.agents.tools.shell_expert.ask_confirm", return_value="y"
    )
    with mock_llm(
        mocker,
        [
            '{"tool": "shell_expert", "arg": "say how are you", "thoughts": "test"}',
            "```sh\necho fine thanks\n```",
            "fine thanks",
        ],
    ):
        result = exec("-o -x how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "💻 Generating shell script..." in result.stdout
        assert confirm.call_count == 0
        assert "echo fine thanks" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_python_expert_tool(exec, mocker):
    confirm = mocker.patch(
        "shy_sh.agents.tools.python_expert.ask_confirm", return_value="y"
    )
    with mock_llm(
        mocker,
        [
            '{"tool": "python_expert", "arg": "say how are you", "thoughts": "test"}',
            "```python\nprint('fine thanks')\n```",
            "fine thanks",
        ],
    ):
        result = exec("-o how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "🐍 Generating python script..." in result.stdout
        assert confirm.call_count == 1
        assert "print('fine thanks')" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_python_expert_tool_no_confirmation(exec, mocker):
    confirm = mocker.patch(
        "shy_sh.agents.tools.python_expert.ask_confirm", return_value="y"
    )
    with mock_llm(
        mocker,
        [
            '{"tool": "python_expert", "arg": "say how are you", "thoughts": "test"}',
            "```python\nprint('fine thanks')\n```",
            "fine thanks",
        ],
    ):
        result = exec("-o -x how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "🐍 Generating python script..." in result.stdout
        assert confirm.call_count == 0
        assert "print('fine thanks')" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_shell_history_tool(exec, mocker):
    with mock_llm(
        mocker,
        [
            '{"tool": "shell_history", "arg": "", "thoughts": "test"}',
            "history readed",
        ],
    ):
        result = exec("-o how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "📜 Let me check..." in result.stdout
        assert "These are the last commands executed by the user:" not in result.stdout
        assert "🤖: history readed" in result.stdout


def test_use_tool_chain(exec, mocker):
    with mock_llm(
        mocker,
        [
            '{"tool": "shell", "arg": "echo fine thanks", "thoughts": "test"}',
            '{"tool": "shell_expert", "arg": "say how are you with shell", "thoughts": "test"}',
            "```sh\necho fine thanks\n```",
            '{"tool": "python_expert", "arg": "say how are you", "thoughts": "test"}',
            "```python\nprint('fine thanks')\n```",
            "fine thanks",
        ],
    ):
        result = exec("-o -x how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "🛠️  echo fine thanks" in result.stdout
        assert "💻 Generating shell script..." in result.stdout
        assert "🐍 Generating python script..." in result.stdout
        assert "🤖: fine thanks" in result.stdout
