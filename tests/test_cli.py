import yaml
from tests.utils import mock_llm


def test_version(exec):
    result = exec("--version")
    assert result.exit_code == 0
    assert result.stdout.startswith("Version: ")


def test_question(exec, mocker):
    with mock_llm(mocker):
        result = exec("how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "🤖: test" in result.stdout


def test_interactive_question(exec, mocker):
    with mock_llm(mocker, ["fine thanks"]):
        result = exec("-i how are you", input="exit\n")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "🤖: fine thanks" in result.stdout
        assert "👋 Bye!" in result.stdout


def test_use_shell_tool(exec, mocker):
    with mock_llm(
        mocker,
        [
            '{"tool": "shell", "arg": "echo fine thanks", "thoughts": "test"}',
            "fine thanks",
        ],
    ):
        result = exec("how are you", input="y\n")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "Do you want to execute this command? [Y/n/c]" in result.stdout
        assert "🛠️ echo fine thanks" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_shell_tool_no_confirmation(exec, mocker):
    with mock_llm(
        mocker,
        [
            '{"tool": "shell", "arg": "echo fine thanks", "thoughts": "test"}',
            "fine thanks",
        ],
    ):
        result = exec("-x how are you")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "Do you want to execute this command? [Y/n/c]" not in result.stdout
        assert "🛠️ echo fine thanks" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_shell_expert_tool(exec, mocker):
    with mock_llm(
        mocker,
        [
            '{"tool": "shell_expert", "arg": "say how are you", "thoughts": "test"}',
            "```sh\necho fine thanks\n```",
            "fine thanks",
        ],
    ):
        result = exec("how are you", input="y\n")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "💻 Generating shell script..." in result.stdout
        assert "Do you want to execute this command? [Y/n/c]" in result.stdout
        assert "echo fine thanks" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_shell_expert_tool_no_confirmation(exec, mocker):
    with mock_llm(
        mocker,
        [
            '{"tool": "shell_expert", "arg": "say how are you", "thoughts": "test"}',
            "```sh\necho fine thanks\n```",
            "fine thanks",
        ],
    ):
        result = exec("-x how are you", input="y\n")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "💻 Generating shell script..." in result.stdout
        assert "Do you want to execute this command? [Y/n/c]" not in result.stdout
        assert "echo fine thanks" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_python_expert_tool(exec, mocker):
    with mock_llm(
        mocker,
        [
            '{"tool": "python_expert", "arg": "say how are you", "thoughts": "test"}',
            "```python\nprint('fine thanks')\n```",
            "fine thanks",
        ],
    ):
        result = exec("how are you", input="y\n")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "🐍 Generating python script..." in result.stdout
        assert "Do you want to execute this command? [Y/n/c]" in result.stdout
        assert "print('fine thanks')" in result.stdout
        assert "🤖: fine thanks" in result.stdout


def test_use_python_expert_tool_no_confirmation(exec, mocker):
    with mock_llm(
        mocker,
        [
            '{"tool": "python_expert", "arg": "say how are you", "thoughts": "test"}',
            "```python\nprint('fine thanks')\n```",
            "fine thanks",
        ],
    ):
        result = exec("-x how are you", input="y\n")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "🐍 Generating python script..." in result.stdout
        assert "Do you want to execute this command? [Y/n/c]" not in result.stdout
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
        result = exec("how are you", input="y\n")
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
        result = exec("-x how are you", input="y\n")
        assert result.exit_code == 0

        assert "✨: how are you" in result.stdout
        assert "🛠️ echo fine thanks" in result.stdout
        assert "💻 Generating shell script..." in result.stdout
        assert "🐍 Generating python script..." in result.stdout
        assert "🤖: fine thanks" in result.stdout
