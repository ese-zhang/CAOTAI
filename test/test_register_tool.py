"""
backend.core.tools.register_tool 全覆盖测试
"""
from unittest.mock import patch


import pytest

from backend.core.tools.register_tool import (
    MAX_READ_LINES,
    GREP_CONTEXT_LINES,
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


class TestGetWeather:
    def test_returns_city_weather(self):
        assert get_weather("北京") == "北京今天晴天"
        assert get_weather("上海") == "上海今天晴天"


class TestListDirectory:
    def test_nonexistent_path_returns_empty(self):
        assert list_directory("/nonexistent/path/xyz", 0) == []

    def test_file_path_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x")
        assert list_directory(str(f), 0) == []

    def test_empty_dir_depth_zero(self, tmp_path):
        assert list_directory(str(tmp_path), 0) == []

    def test_depth_zero_lists_immediate_children(self, tmp_path):
        (tmp_path / "a.txt").write_text("")
        (tmp_path / "b").mkdir()
        (tmp_path / "c.py").write_text("")
        result = list_directory(str(tmp_path), 0)
        assert "a.txt" in result
        assert "c.py" in result
        assert any("b" in r for r in result)

    def test_depth_minus_one_lists_all(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b.txt").write_text("")
        (tmp_path / "c.txt").write_text("")
        result = list_directory(str(tmp_path), -1)
        assert len(result) >= 2
        assert any("c.txt" in r for r in result)
        assert any("b.txt" in r for r in result)

    def test_depth_one_limits_depth(self, tmp_path):
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir1" / "deep").mkdir()
        (tmp_path / "dir1" / "deep" / "very_deep.txt").write_text("")
        result = list_directory(str(tmp_path), 1)
        assert any("dir1" in r for r in result)
        assert not any("very_deep" in r for r in result)

    def test_list_directory_exception_returns_empty(self):
        with patch("backend.core.tools.register_tool.Path") as MockPath:
            mock_p = MockPath.return_value
            mock_p.resolve.side_effect = OSError("bad")
            assert list_directory("any", 0) == []


class TestListModules:
    def test_nonexistent_file_returns_empty(self):
        assert list_modules("/nonexistent/file.py", 0) == []

    def test_non_py_file_returns_empty(self, tmp_path):
        (tmp_path / "f.txt").write_text("x")
        assert list_modules(str(tmp_path / "f.txt"), 0) == []

    def test_depth_zero_lists_classes_and_functions(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text(
            "def foo(): pass\nclass Bar: pass\nclass Baz: pass\n"
        )
        result = list_modules(str(py), 0)
        assert "foo" in result
        assert "Bar" in result
        assert "Baz" in result
        assert result == sorted(result)

    def test_depth_nonzero_lists_imports(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text("import os\nfrom pathlib import Path\n")
        result = list_modules(str(py), 1)
        assert "os" in result
        assert "Path" in result

    def test_syntax_error_returns_empty(self, tmp_path):
        py = tmp_path / "bad.py"
        py.write_text("def ( invalid\n")
        assert list_modules(str(py), 0) == []


class TestReadFile:
    def test_nonexistent_returns_empty(self):
        assert read_file("/nonexistent", 1, 10) == ""

    def test_directory_returns_empty(self, tmp_path):
        assert read_file(str(tmp_path), 1, 10) == ""

    def test_reads_range(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("line1\nline2\nline3\nline4\n")
        assert read_file(str(f), 1, 3) == "line1\nline2\nline3"
        assert read_file(str(f), 2, 2) == "line2"

    def test_start_after_end_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("line1\n")
        assert read_file(str(f), 2, 1) == ""

    def test_over_threshold_appends_message(self, tmp_path):
        f = tmp_path / "f.txt"
        lines = ["line" + str(i) for i in range(MAX_READ_LINES + 100)]
        f.write_text("\n".join(lines))
        out = read_file(str(f), 1, len(lines) + 1)
        assert "仅显示" in out
        assert str(MAX_READ_LINES) in out
        assert "分批读取" in out

    def test_read_file_exception_returns_empty(self):
        with patch("backend.core.tools.register_tool.Path") as MockPath:
            mock_p = MockPath.return_value
            mock_p.resolve.return_value = mock_p
            mock_p.exists.return_value = True
            mock_p.is_file.return_value = True
            mock_p.read_text.side_effect = OSError("read error")
            assert read_file("x", 1, 10) == ""


class TestReadModule:
    def test_nonexistent_returns_message(self):
        assert "不存在" in read_module("/nonexistent/x.py", "Foo")

    def test_non_py_returns_message(self, tmp_path):
        (tmp_path / "f.txt").write_text("x")
        assert "仅支持" in read_module(str(tmp_path / "f.txt"), "Foo")

    def test_found_function_returns_source(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text("def hello():\n    return 42\n")
        out = read_module(str(py), "hello")
        assert "def hello" in out
        assert "return 42" in out

    def test_found_class_returns_source(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text("class Foo:\n    x = 1\n")
        out = read_module(str(py), "Foo")
        assert "class Foo" in out
        assert "x = 1" in out

    def test_not_found_returns_message(self, tmp_path):
        py = tmp_path / "m.py"
        py.write_text("def only(): pass\n")
        assert "未找到" in read_module(str(py), "Missing")

    def test_syntax_error_returns_message(self, tmp_path):
        py = tmp_path / "bad.py"
        py.write_text("def ( bad\n")
        assert "语法错误" in read_module(str(py), "x")

    def test_read_module_exception_returns_failure_message(self):
        with patch("backend.core.tools.register_tool.Path") as MockPath:
            mock_p = MockPath.return_value
            mock_p.resolve.return_value = mock_p
            mock_p.exists.return_value = True
            mock_p.is_file.return_value = True
            mock_p.suffix = ".py"
            mock_p.read_text.side_effect = RuntimeError("io error")
            assert "读取失败" in read_module("x.py", "Foo")


class TestGrep:
    def test_nonexistent_returns_empty(self):
        assert grep("/nonexistent", "x") == []

    def test_directory_returns_empty(self, tmp_path):
        assert grep(str(tmp_path), "x") == []

    def test_invalid_regex_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hello\n")
        assert grep(str(f), "[invalid(regex") == []

    def test_match_returns_context(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nmatch_here\nc\nd\n")
        result = grep(str(f), "match_here")
        assert len(result) == 1
        assert result[0]["line"] == 3
        assert "match_here" in result[0]["content"]
        assert "context" in result[0]
        assert "2:" in result[0]["context"]
        assert "4:" in result[0]["context"]

    def test_no_match_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        assert grep(str(f), "nomatch") == []

    def test_multiple_matches(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x\nfoo\nbar\nfoo\n")
        result = grep(str(f), "foo")
        assert len(result) == 2
        assert result[0]["line"] == 2
        assert result[1]["line"] == 4

    def test_grep_exception_returns_empty(self):
        with patch("backend.core.tools.register_tool.Path") as MockPath:
            mock_p = MockPath.return_value
            mock_p.resolve.return_value = mock_p
            mock_p.exists.return_value = True
            mock_p.is_file.return_value = True
            mock_p.read_text.side_effect = OSError("read error")
            assert grep("x", "a") == []


class TestApplyDiff:
    def test_nonexistent_file_returns_empty(self):
        assert apply_diff("/nonexistent", "a", "b", [1], False) == ""

    def test_exact_replace_single(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hello world")
        out = apply_diff(str(f), "world", "python", [1], False)
        assert out == "hello python"

    def test_replace_all_when_occurence_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a x b x c")
        out = apply_diff(str(f), " x ", " ", [], False)
        assert out == "a b c"

    def test_replace_specific_occurrence(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x and x and x")
        out = apply_diff(str(f), "x", "Y", [2], False)
        assert out == "x and Y and x"

    def test_apply_diff_occurence_default_is_first(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a x b x c")
        out = apply_diff(str(f), " x ", " ", None, False)
        assert out == "a b x c"

    def test_apply_diff_skip_some_occurrences(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("X\nX\nX\n")
        out = apply_diff(str(f), "X", "Y", [1, 3], False)
        assert out == "Y\nX\nY\n"
        # 覆盖 else 分支：只替换部分匹配项时，未选中的匹配保留
        f2 = tmp_path / "f2.txt"
        f2.write_text("__A__ __A__ __A__")
        out2 = apply_diff(str(f2), "__A__", "X", [2], False)
        assert out2 == "__A__ X __A__"

    def test_no_match_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hello")
        assert apply_diff(str(f), "xyz", "a", [1], False) == ""

    def test_fuzzy_no_match_low_similarity_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("completely different content")
        assert apply_diff(str(f), "search_block", "replace", [1], True) == ""

    def test_fuzzy_match_replaces(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("line1\nline2\nline3\nline4\n")
        search = "line2\nline3"
        replace = "replaced"
        out = apply_diff(str(f), search, replace, [1], True)
        assert "replaced" in out
        assert "line2" not in out or "line1" in out

    def test_fuzzy_low_similarity_returns_empty(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("aaaa\nbbbb\ncccc\n")
        # 与内容相似度很低的搜索块，无法达到 0.6
        out = apply_diff(str(f), "xyz\nqwerty", "repl", [1], True)
        assert out == ""

    def test_apply_diff_exception_returns_empty(self):
        with patch("backend.core.tools.register_tool.Path") as MockPath:
            mock_p = MockPath.return_value
            mock_p.resolve.return_value = mock_p
            mock_p.exists.return_value = True
            mock_p.is_file.return_value = True
            mock_p.read_text.side_effect = OSError("read error")
            assert apply_diff("x", "a", "b", [1], False) == ""


class TestCreateFile:
    def test_creates_file_and_returns_true(self, tmp_path):
        p = tmp_path / "sub" / "new.txt"
        assert create_file(str(p), "content") is True
        assert p.read_text() == "content"

    def test_existing_file_returns_false(self, tmp_path):
        f = tmp_path / "existing.txt"
        f.write_text("old")
        assert create_file(str(f), "new") is False
        assert f.read_text() == "old"

    def test_invalid_path_returns_false(self):
        # 通过 mock 使 mkdir 或 write_text 抛出异常，验证返回 False
        from unittest.mock import patch, MagicMock
        with patch("backend.core.tools.register_tool.Path") as MockPath:
            mock_path = MagicMock()
            mock_path.resolve.return_value = mock_path
            mock_path.exists.return_value = False
            mock_path.parent.mkdir.side_effect = OSError("permission denied")
            MockPath.return_value = mock_path
            assert create_file("any/path", "x") is False

    def test_create_file_write_exception_returns_false(self, tmp_path):
        from unittest.mock import patch, MagicMock
        p = tmp_path / "new.txt"
        with patch("backend.core.tools.register_tool.Path") as MockPath:
            mock_path = MagicMock()
            mock_path.resolve.return_value = mock_path
            mock_path.exists.return_value = False
            mock_path.parent.mkdir.return_value = None
            mock_path.write_text.side_effect = OSError("disk full")
            MockPath.return_value = mock_path
            assert create_file(str(p), "x") is False


class TestRunShellCommand:
    def test_returns_stdout(self):
        out = run_shell_command("echo hello")
        assert "hello" in out

    def test_failure_returns_error_message(self):
        out = run_shell_command("exit 1")
        assert isinstance(out, str)

    @patch("backend.core.tools.register_tool.subprocess.run")
    def test_exception_returns_str(self, mock_run):
        mock_run.side_effect = OSError("bad")
        out = run_shell_command("anything")
        assert "bad" in out


class TestToolManagerRegistration:
    """确保所有工具均在 tool_manager 中注册并可被调用"""

    def test_get_weather_registered(self):
        from backend.core.tools import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["get_weather"])
        assert len(tools_list) == 1
        assert "get_weather" in registry
        assert registry["get_weather"]("北京") == "北京今天晴天"

    def test_list_directory_registered(self):
        from backend.core.tools import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["list_directory"])
        assert "list_directory" in registry

    def test_list_modules_registered(self):
        from backend.core.tools import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["list_modules"])
        assert "list_modules" in registry

    def test_read_file_registered(self):
        from backend.core.tools import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["read_file"])
        assert "read_file" in registry

    def test_read_module_registered(self):
        from backend.core.tools import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["read_module"])
        assert "read_module" in registry

    def test_grep_registered(self):
        from backend.core.tools import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["grep"])
        assert "grep" in registry

    def test_apply_diff_registered(self):
        from backend.core.tools import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["apply_diff"])
        assert "apply_diff" in registry

    def test_create_file_registered(self):
        from backend.core.tools import tool_manager
        tools_list, registry = tool_manager.get_payload_components(["create_file"])
        assert "create_file" in registry
