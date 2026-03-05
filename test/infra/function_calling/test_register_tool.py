"""
backend.infra.function_calling.register_tool 全覆盖测试
工具签名为 (ctx: ToolContext, **kwargs)，测试与外界解耦，仅注入 ctx。
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.infra.function_calling.context import ToolContext
from backend.infra.function_calling.register_tool import (
    MAX_READ_LINES,
    get_weather,
    list_directory,
    list_modules,
    read_file,
    read_module,
    grep,
    apply_diff,
    create_file,
    run_shell_command,
)


def _ctx(workspace_root):
    """测试用上下文，不依赖 app/skills_manager。"""
    return ToolContext(workspace_root=Path(workspace_root), skills_provider=None)


class TestGetWeather:
    def test_returns_city_weather(self):
        ctx = _ctx(Path.cwd())
        assert get_weather(ctx, "北京") == "北京今天晴天"
        assert get_weather(ctx, "上海") == "上海今天晴天"


class TestListDirectory:
    def test_nonexistent_path_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        assert list_directory(ctx, "nonexistent_xyz", 0) == []

    def test_file_path_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x")
        ctx = _ctx(tmp_path)
        assert list_directory(ctx, "f.txt", 0) == []

    def test_empty_dir_depth_zero(self, tmp_path):
        ctx = _ctx(tmp_path)
        assert list_directory(ctx, ".", 0) == []

    def test_depth_zero_lists_immediate_children(self, tmp_path):
        (tmp_path / "a.txt").write_text("")
        (tmp_path / "b").mkdir()
        (tmp_path / "c.py").write_text("")
        ctx = _ctx(tmp_path)
        result = list_directory(ctx, ".", 0)
        assert "a.txt" in result
        assert "c.py" in result
        assert any("b" in r for r in result)

    def test_depth_minus_one_lists_all(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b.txt").write_text("")
        (tmp_path / "c.txt").write_text("")
        ctx = _ctx(tmp_path)
        result = list_directory(ctx, ".", -1)
        assert len(result) >= 2
        assert any("c.txt" in r for r in result)
        assert any("b.txt" in r for r in result)

    def test_depth_one_limits_depth(self, tmp_path):
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir1" / "deep").mkdir()
        (tmp_path / "dir1" / "deep" / "very_deep.txt").write_text("")
        ctx = _ctx(tmp_path)
        result = list_directory(ctx, ".", 1)
        assert any("dir1" in r for r in result)
        assert not any("very_deep" in r for r in result)

    def test_list_directory_exception_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        with patch.object(ctx, "resolve_path", side_effect=OSError("bad")):
            assert list_directory(ctx, "any", 0) == []


class TestListModules:
    def test_nonexistent_file_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        assert list_modules(ctx, "nonexistent_file.py", 0) == []

    def test_non_py_file_returns_empty(self, tmp_path):
        (tmp_path / "f.txt").write_text("x")
        ctx = _ctx(tmp_path)
        assert list_modules(ctx, "f.txt", 0) == []

    def test_depth_zero_lists_classes_and_functions(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text(
            "def foo(): pass\nclass Bar: pass\nclass Baz: pass\n"
        )
        ctx = _ctx(tmp_path)
        result = list_modules(ctx, "m.py", 0)
        assert "foo" in result
        assert "Bar" in result
        assert "Baz" in result
        assert result == sorted(result)

    def test_depth_one_lists_class_methods(self, tmp_path):
        py = tmp_path / "agent.py"
        py.write_text(
            "class basic_agent:\n"
            "    def __init__(self): pass\n"
            "    def get_payload(self): pass\n"
            "    def run(self, request): pass\n"
            "    def prompt_builder(self): pass\n"
        )
        ctx = _ctx(tmp_path)
        result = list_modules(ctx, "agent.py", 1)
        assert "basic_agent.__init__" in result
        assert "basic_agent.get_payload" in result
        assert "basic_agent.run" in result
        assert "basic_agent.prompt_builder" in result

    def test_depth_zero_only_top_level(self, tmp_path):
        py = tmp_path / "agent.py"
        py.write_text(
            "class basic_agent:\n"
            "    def run(self): pass\n"
        )
        ctx = _ctx(tmp_path)
        result = list_modules(ctx, "agent.py", 0)
        assert result == ["basic_agent"]

    def test_syntax_error_returns_empty(self, tmp_path):
        py = tmp_path / "bad.py"
        py.write_text("def ( invalid\n")
        ctx = _ctx(tmp_path)
        assert list_modules(ctx, "bad.py", 0) == []


class TestReadFile:
    def test_nonexistent_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        assert read_file(ctx, "nonexistent", 1, 10) == ""

    def test_directory_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        assert read_file(ctx, ".", 1, 10) == ""

    def test_reads_range(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("line1\nline2\nline3\nline4\n")
        ctx = _ctx(tmp_path)
        assert read_file(ctx, "f.txt", 1, 3) == "line1\nline2\nline3"
        assert read_file(ctx, "f.txt", 2, 2) == "line2"

    def test_start_after_end_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("line1\n")
        ctx = _ctx(tmp_path)
        assert read_file(ctx, "f.txt", 2, 1) == ""

    def test_over_threshold_appends_message(self, tmp_path):
        f = tmp_path / "f.txt"
        lines = ["line" + str(i) for i in range(MAX_READ_LINES + 100)]
        f.write_text("\n".join(lines))
        ctx = _ctx(tmp_path)
        out = read_file(ctx, "f.txt", 1, len(lines) + 1)
        assert "仅显示" in out
        assert str(MAX_READ_LINES) in out
        assert "分批读取" in out

    def test_read_file_exception_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        mock_p = MagicMock()
        mock_p.exists.return_value = True
        mock_p.is_file.return_value = True
        mock_p.read_text.side_effect = OSError("read error")
        with patch.object(ctx, "resolve_path", return_value=mock_p):
            assert read_file(ctx, "x", 1, 10) == ""


class TestReadModule:
    def test_nonexistent_returns_message(self, tmp_path):
        ctx = _ctx(tmp_path)
        assert "不存在" in read_module(ctx, "nonexistent/x.py", "Foo")

    def test_non_py_returns_message(self, tmp_path):
        (tmp_path / "f.txt").write_text("x")
        ctx = _ctx(tmp_path)
        assert "仅支持" in read_module(ctx, "f.txt", "Foo")

    def test_found_function_returns_source(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text("def hello():\n    return 42\n")
        ctx = _ctx(tmp_path)
        out = read_module(ctx, "m.py", "hello")
        assert "def hello" in out
        assert "return 42" in out

    def test_found_class_returns_source(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text("class Foo:\n    x = 1\n")
        ctx = _ctx(tmp_path)
        out = read_module(ctx, "m.py", "Foo")
        assert "class Foo" in out
        assert "x = 1" in out

    def test_not_found_returns_message(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text("def only(): pass\n")
        ctx = _ctx(tmp_path)
        assert "未找到" in read_module(ctx, "m.py", "Missing")

    def test_syntax_error_returns_message(self, tmp_path):
        py = tmp_path / "bad.py"
        py.write_text("def ( bad\n")
        ctx = _ctx(tmp_path)
        assert "语法错误" in read_module(ctx, "bad.py", "x")

    def test_read_module_exception_returns_failure_message(self, tmp_path):
        ctx = _ctx(tmp_path)
        mock_p = MagicMock()
        mock_p.exists.return_value = True
        mock_p.is_file.return_value = True
        mock_p.suffix = ".py"
        mock_p.read_text.side_effect = RuntimeError("io error")
        with patch.object(ctx, "resolve_path", return_value=mock_p):
            assert "读取失败" in read_module(ctx, "x.py", "Foo")

    def test_class_method_with_qualified_name(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text(
            "class Foo:\n"
            "    def bar(self):\n"
            "        return 1\n"
        )
        ctx = _ctx(tmp_path)
        out = read_module(ctx, "m.py", "Foo.bar")
        assert "def bar" in out
        assert "return 1" in out

    def test_ambiguous_method_prefers_qualified(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text(
            "class A:\n"
            "    def foo(self):\n"
            "        return 'A'\n"
            "\n"
            "class B:\n"
            "    def foo(self):\n"
            "        return 'B'\n"
        )
        ctx = _ctx(tmp_path)
        out1 = read_module(ctx, "m.py", "foo")
        assert "return 'A'" in out1
        assert "return 'B'" not in out1
        out2 = read_module(ctx, "m.py", "B.foo")
        assert "return 'B'" in out2
        assert "return 'A'" not in out2


class TestGrep:
    def test_nonexistent_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        assert grep(ctx, "nonexistent", "x") == []

    def test_directory_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        assert grep(ctx, ".", "x") == []

    def test_invalid_regex_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hello\n")
        ctx = _ctx(tmp_path)
        assert grep(ctx, "f.txt", "[invalid(regex") == []

    def test_match_returns_context(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nmatch_here\nc\nd\n")
        ctx = _ctx(tmp_path)
        result = grep(ctx, "f.txt", "match_here")
        assert len(result) == 1
        assert result[0]["line"] == 3
        assert "match_here" in result[0]["content"]
        assert "context" in result[0]
        assert "2:" in result[0]["context"]
        assert "4:" in result[0]["context"]

    def test_no_match_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        ctx = _ctx(tmp_path)
        assert grep(ctx, "f.txt", "nomatch") == []

    def test_multiple_matches(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x\nfoo\nbar\nfoo\n")
        ctx = _ctx(tmp_path)
        result = grep(ctx, "f.txt", "foo")
        assert len(result) == 2
        assert result[0]["line"] == 2
        assert result[1]["line"] == 4

    def test_grep_exception_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        mock_p = MagicMock()
        mock_p.exists.return_value = True
        mock_p.is_file.return_value = True
        mock_p.read_text.side_effect = OSError("read error")
        with patch.object(ctx, "resolve_path", return_value=mock_p):
            assert grep(ctx, "x", "a") == []


class TestApplyDiff:
    def test_nonexistent_file_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        assert apply_diff(ctx, "nonexistent", "a", "b", [1], False) == ""

    def test_exact_replace_single(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hello world")
        ctx = _ctx(tmp_path)
        out = apply_diff(ctx, "f.txt", "world", "python", [1], False)
        assert out == "hello python"

    def test_replace_all_when_occurence_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a x b x c")
        ctx = _ctx(tmp_path)
        out = apply_diff(ctx, "f.txt", " x ", " ", [], False)
        assert out == "a b c"

    def test_replace_specific_occurrence(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x and x and x")
        ctx = _ctx(tmp_path)
        out = apply_diff(ctx, "f.txt", "x", "Y", [2], False)
        assert out == "x and Y and x"

    def test_apply_diff_occurence_default_is_first(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a x b x c")
        ctx = _ctx(tmp_path)
        out = apply_diff(ctx, "f.txt", " x ", " ", None, False)
        assert out == "a b x c"

    def test_apply_diff_skip_some_occurrences(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("X\nX\nX\n")
        ctx = _ctx(tmp_path)
        out = apply_diff(ctx, "f.txt", "X", "Y", [1, 3], False)
        assert out == "Y\nX\nY\n"
        f2 = tmp_path / "f2.txt"
        f2.write_text("__A__ __A__ __A__")
        out2 = apply_diff(ctx, "f2.txt", "__A__", "X", [2], False)
        assert out2 == "__A__ X __A__"

    def test_no_match_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hello")
        ctx = _ctx(tmp_path)
        assert apply_diff(ctx, "f.txt", "xyz", "a", [1], False) == ""

    def test_fuzzy_no_match_low_similarity_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("completely different content")
        ctx = _ctx(tmp_path)
        assert apply_diff(ctx, "f.txt", "search_block", "replace", [1], True) == ""

    def test_fuzzy_match_replaces(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("line1\nline2\nline3\nline4\n")
        ctx = _ctx(tmp_path)
        out = apply_diff(ctx, "f.txt", "line2\nline3", "replaced", [1], True)
        assert "replaced" in out
        assert "line2" not in out or "line1" in out

    def test_fuzzy_low_similarity_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("aaaa\nbbbb\ncccc\n")
        ctx = _ctx(tmp_path)
        out = apply_diff(ctx, "f.txt", "xyz\nqwerty", "repl", [1], True)
        assert out == ""

    def test_apply_diff_exception_returns_empty(self, tmp_path):
        ctx = _ctx(tmp_path)
        mock_p = MagicMock()
        mock_p.exists.return_value = True
        mock_p.is_file.return_value = True
        mock_p.read_text.side_effect = OSError("read error")
        with patch.object(ctx, "resolve_path", return_value=mock_p):
            assert apply_diff(ctx, "x", "a", "b", [1], False) == ""


class TestCreateFile:
    def test_creates_file_and_returns_true(self, tmp_path):
        ctx = _ctx(tmp_path)
        assert create_file(ctx, "sub/new.txt", "content") is True
        assert (tmp_path / "sub" / "new.txt").read_text() == "content"

    def test_existing_file_returns_false(self, tmp_path):
        f = tmp_path / "existing.txt"
        f.write_text("old")
        ctx = _ctx(tmp_path)
        assert create_file(ctx, "existing.txt", "new") is False
        assert f.read_text() == "old"

    def test_invalid_path_returns_false(self, tmp_path):
        ctx = _ctx(tmp_path)
        mock_p = MagicMock()
        mock_p.exists.return_value = False
        mock_p.parent.mkdir.side_effect = OSError("permission denied")
        with patch.object(ctx, "resolve_path", return_value=mock_p):
            assert create_file(ctx, "any/path", "x") is False

    def test_create_file_write_exception_returns_false(self, tmp_path):
        ctx = _ctx(tmp_path)
        mock_p = MagicMock()
        mock_p.exists.return_value = False
        mock_p.parent.mkdir.return_value = None
        mock_p.write_text.side_effect = OSError("disk full")
        with patch.object(ctx, "resolve_path", return_value=mock_p):
            assert create_file(ctx, "new.txt", "x") is False


class TestRunShellCommand:
    def test_returns_stdout(self):
        ctx = _ctx(Path.cwd())
        out = run_shell_command(ctx, "echo hello")
        assert "hello" in out

    def test_failure_returns_error_message(self):
        ctx = _ctx(Path.cwd())
        out = run_shell_command(ctx, "exit 1")
        assert isinstance(out, str)

    @patch("backend.infra.function_calling.register_tool.subprocess.run")
    def test_exception_returns_str(self, mock_run):
        mock_run.side_effect = OSError("bad")
        ctx = _ctx(Path.cwd())
        out = run_shell_command(ctx, "anything")
        assert "bad" in out


class TestToolManagerRegistration:
    """确保所有工具均在 tool_manager 中注册并可被调用（测试与外界解耦，仅注入 ctx）"""

    def test_get_weather_registered(self):
        from backend.infra.function_calling import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["get_weather"])
        assert len(tools_list) == 1
        assert "get_weather" in registry
        ctx = _ctx(Path.cwd())
        assert registry["get_weather"](ctx, "北京") == "北京今天晴天"

    def test_list_directory_registered(self):
        from backend.infra.function_calling import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["list_directory"])
        assert "list_directory" in registry

    def test_list_modules_registered(self):
        from backend.infra.function_calling import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["list_modules"])
        assert "list_modules" in registry

    def test_read_file_registered(self):
        from backend.infra.function_calling import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["read_file"])
        assert "read_file" in registry

    def test_read_module_registered(self):
        from backend.infra.function_calling import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["read_module"])
        assert "read_module" in registry

    def test_grep_registered(self):
        from backend.infra.function_calling import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["grep"])
        assert "grep" in registry

    def test_apply_diff_registered(self):
        from backend.infra.function_calling import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["apply_diff"])
        assert "apply_diff" in registry

    def test_create_file_registered(self):
        from backend.infra.function_calling import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["create_file"])
        assert "create_file" in registry
