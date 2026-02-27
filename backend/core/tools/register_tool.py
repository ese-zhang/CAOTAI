from . import tool_manager
import ast
import difflib
import os
import re
import subprocess
from pathlib import Path

tools_list = [
    "list_directory",
    "list_modules",
    "read_file",
    "read_module",
    "grep",
    "apply_diff",
    "create_file",
    "run_shell_command",
    "get_weather",
]
# read_file 行数差距阈值，超过则只返回前 MAX_READ_LINES 行并提示
MAX_READ_LINES = 500
# grep 上下文行数
GREP_CONTEXT_LINES = 2

@tool_manager.register(
    name="get_weather",
    description="获取指定城市的天气",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名称，如北京、上海"}
        },
        "required": ["city"]
    }
)
def get_weather(city: str):
    return f"{city}今天晴天"


@tool_manager.register(
    name="list_directory",
    description="列出指定路径下的所有文件和文件夹",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要列出的路径"},
            "depth": {"type": "integer", "description": "深度,-1为所有"}
        },
        "required": ["path", "depth"]
    }
)
def list_directory(path: str, depth: int) -> list:
    """
        列出指定路径下的所有文件和文件夹
        :param path: 要列出的路径
        :param depth: 深度,-1为所有
        :return: 文件和文件夹的列表
    """
    try:
        root = Path(path).resolve()
        if not root.exists() or not root.is_dir():
            return []
        result = []
        if depth == -1:
            for dirpath, dirnames, filenames in os.walk(root):
                rel = Path(dirpath).relative_to(root)
                for d in dirnames:
                    result.append(str(rel / d) + os.sep)
                for f in filenames:
                    result.append(str(rel / f))
        else:
            for dirpath, dirnames, filenames in os.walk(root):
                rel = Path(dirpath).relative_to(root)
                current_depth = 0 if rel.parts == (".",) else len(rel.parts)
                if current_depth > depth:
                    del dirnames[:]
                    continue
                for d in dirnames:
                    result.append(str(rel / d) + os.sep)
                for f in filenames:
                    result.append(str(rel / f))
        return sorted(set(result))
    except Exception:
        return []


@tool_manager.register(
    name="list_modules",
    description="列出指定文件内的所有类或函数，展开层级可设置",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "要列出的文件路径"},
            "module_depth": {"type": "integer", "description": "模块的深度,正整数,0为top，1包含top的子类或方法，以此类推"}
        },
        "required": ["file_path", "module_depth"]
    }
)
def list_modules(file_path: str, module_depth: int) -> list:
    """
        列出指定文件内的所有模块
        :param file_path: 要列出的python文件路径
        :param module_depth: 0=当前文件(顶层类/函数), 1=子模块(类内方法), 2=子模块的子模块, 以此类推
        :return: 模块的列表
    """
    try:
        path = Path(file_path).resolve()
        if not path.exists() or path.suffix != ".py":
            return []
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
        result = []

        def collect(body: list, depth: int, prefix: str = ""):
            if depth < 0:
                return
            for node in body:
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    name = f"{prefix}{node.name}" if prefix else node.name
                    if depth == 0:
                        result.append(name)
                    else:
                        collect(node.body, depth - 1, f"{name}.")

        collect(tree.body, module_depth)
        return sorted(result)
    except (SyntaxError, OSError):
        return []

@tool_manager.register(
    name="read_file",
    description="读取指定路径下的文件,并返回指定行数的内容",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要读取的文件路径"},
            "start_lines": {"type": "integer", "description": "开始行数"},
            "end_lines": {"type": "integer", "description": "结束行数"}
        },
        "required": ["path", "start_lines", "end_lines"]
    }
)
def read_file(path: str, start_lines: int, end_lines: int) -> str:
    """
        读取指定路径下的文件,并返回指定行数的内容,
        如果差距超过阈值, 则返回start_lines到阈值行数的内容, 并提示用户需要读取更多行数
        :param path: 要读取的文件路径
        :param start_lines: 开始行数
        :param end_lines: 结束行数
        :return: 指定行数的内容, 如果差距超过阈值, 则返回start_lines到阈值行数的内容, 并提示用户需要读取更多行数
    """
    try:
        p = Path(path).resolve()
        if not p.exists() or not p.is_file():
            return ""
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(0, start_lines - 1)
        end = min(len(lines), end_lines)
        if start >= end:
            return ""
        span = end - start
        if span > MAX_READ_LINES:
            end = start + MAX_READ_LINES
            content = "\n".join(lines[start:end])
            content += f"\n\n[仅显示 {MAX_READ_LINES} 行，共需 {span} 行。请缩小范围或分批读取。]"
            return content
        return "\n".join(lines[start:end])
    except Exception:
        return ""

@tool_manager.register(
    name="read_module",
    description="读取指定python文件下读取指定类或函数",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要读取的python文件路径"},
            "module_name": {"type": "string", "description": "要读取的类或函数名称"}
        },
        "required": ["path", "module_name"]
    }
)
def read_module(path: str, module_name: str) -> str:
    """
        读取指定python文件下读取指定类或函数,如果不是python文件则返回提示信息(string)
        :param path: 要读取的python文件路径
        :param module_name: 要读取的类或函数名称
        :return: 类或函数内容
    """
    try:
        p = Path(path).resolve()
        if not p.exists() or not p.is_file():
            return "文件不存在。"
        if p.suffix != ".py":
            return "仅支持读取 Python 文件(.py)。"
        source = p.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        tree = ast.parse(source)

        def find_node(node: ast.AST, name: str):
            """按名称在整棵语法树中查找第一个类或函数定义。"""
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name:
                return node
            for child in ast.iter_child_nodes(node):
                found = find_node(child, name)
                if found is not None:
                    return found
            return None

        def find_by_path(parts: list[str]):
            """
            按 ClassName.method 这种路径精确查找:
            - 前面的部分依次匹配类/函数
            - 最后一段可以是类或函数
            """

            def find_in_body(body, idx: int):
                if idx >= len(parts):
                    return None
                name = parts[idx]
                for node in body:
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name:
                        if idx == len(parts) - 1:
                            return node
                        child_body = getattr(node, "body", [])
                        found = find_in_body(child_body, idx + 1)
                        if found is not None:
                            return found
                return None

            return find_in_body(list(tree.body), 0)

        if "." in module_name:
            target = find_by_path(module_name.split("."))
        else:
            target = find_node(tree, module_name)
        if target is None:
            return f"未找到类或函数: {module_name}"
        start = getattr(target, "lineno", 1) - 1
        end = getattr(target, "end_lineno", len(lines))
        return "\n".join(lines[start:end])
    except SyntaxError:
        return "文件语法错误，无法解析。"
    except Exception:
        return "读取失败。"


@tool_manager.register(
    name="grep",
    description="正则定位。在指定文件中按照正则表达式搜索关键词, 并返回匹配的行数和内容。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "要搜索的文件路径"},
            "regex": {"type": "string", "description": "要搜索的正则表达式"}
        },
        "required": ["file_path", "regex"]
    }
)
def grep(file_path: str, regex: str) -> list:
    """
    正则定位。在指定文件中按照正则表达式搜索关键词, 并返回匹配的行数和内容。
    返回结果应包含 文件名、行号及上下文预览（上下各 2 行）。
    :param file_path: 要搜索的文件路径
    :param regex: 要搜索的正则表达式
    :return: 匹配的行数和内容, 如果文件不存在或没有匹配的行, 则返回空列表
    """
    try:
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return []
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        try:
            pattern = re.compile(regex)
        except re.error:
            return []
        result = []
        for i, line in enumerate(lines):
            if pattern.search(line):
                start = max(0, i - GREP_CONTEXT_LINES)
                end = min(len(lines), i + GREP_CONTEXT_LINES + 1)
                ctx = "\n".join(f"  {start + j + 1}: {lines[j]}" for j in range(start, end))
                result.append({
                    "file": str(p),
                    "line": i + 1,
                    "content": line,
                    "context": ctx,
                })
        return result
    except Exception:
        return []


@tool_manager.register(
    name="apply_diff",
    description="使用搜索替换的方式应用diff到指定文件, 并返回应用diff后的文件内容",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "要应用的文件路径"},
            "search_block": {"type": "string", "description": "要搜索的块"},
            "replace_block": {"type": "string", "description": "要替换的块"},
            "occurence": {"type": "array", "description": "要替换的块的索引列表, 如果为空则替换所有匹配的块"},
            "allow_fuzzy": {"type": "boolean", "description": "是否允许模糊搜索"}
        },
        "required": ["file_path", "search_block", "replace_block", "occurence", "allow_fuzzy"]
    }
)   
def apply_diff(
    file_path: str,
    search_block: str,
    replace_block: str,
    occurence: list[int] | None = None,
    allow_fuzzy: bool = False,
) -> str:
    """
    使用搜索替换的方式应用diff到指定文件, 并返回应用diff后的文件内容
    如果allow_fuzzy为True, 则使用模糊搜索的方式应用diff到指定文件, 并返回应用diff后的文件内容
    :param file_path: 要应用的文件路径
    :param search_block: 要搜索的块
    :param replace_block: 要替换的块
    :param occurence: 要替换的块的索引列表, 如果为空则替换所有匹配的块
    :param allow_fuzzy: 是否允许模糊搜索
    :return: 应用diff后的文件内容, 如果文件不存在或没有匹配的块, 则返回空字符串
    """
    if occurence is None:
        occurence = [1]
    try:
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return ""
        content = p.read_text(encoding="utf-8", errors="replace")
        if allow_fuzzy and search_block not in content:
            lines = content.splitlines()
            search_lines = search_block.splitlines()
            best_ratio, best_start, best_end = 0.0, -1, -1
            for i in range(len(lines) - len(search_lines) + 1):
                chunk = "\n".join(lines[i : i + len(search_lines)])
                r = difflib.SequenceMatcher(None, search_block, chunk).ratio()
                if r > best_ratio:
                    best_ratio, best_start, best_end = r, i, i + len(search_lines)
            if best_ratio >= 0.6 and best_start >= 0:
                new_lines = lines[:best_start] + replace_block.splitlines() + lines[best_end:]
                return "\n".join(new_lines)
            return ""
        indices = list(re.finditer(re.escape(search_block), content))
        if not indices:
            return ""
        replace_all = len(occurence) == 0
        if replace_all:
            return content.replace(search_block, replace_block)
        result = []
        last = 0
        for idx, m in enumerate(indices):
            one_based = idx + 1
            if replace_all or one_based in occurence:
                result.append(content[last : m.start()])
                result.append(replace_block)
                last = m.end()
            else:
                result.append(content[last : m.end()])
                last = m.end()
        result.append(content[last:])
        return "".join(result)
    except Exception:
        return ""

@tool_manager.register(
    name="create_file",
    description="创建指定路径下的文件, 并返回创建后的文件内容",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "要创建的文件路径"},
            "content": {"type": "string", "description": "要创建的文件内容"}
        },
        "required": ["file_path", "content"]
    }
)
def create_file(file_path: str, content: str) -> bool:
    """
    创建指定路径下的文件, 并返回是否创建成功
    如果文件已存在, 则返回False
    :param file_path: 要创建的文件路径
    :param content: 要创建的文件内容
    :return: 是否创建成功
    """
    try:
        p = Path(file_path).resolve()
        if p.exists():
            return False
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False

def run_shell_command(command: str) -> str:
    """
    执行指定shell命令, 并返回执行结果
    如果命令执行失败, 则返回错误信息
    :param command: 要执行的shell命令
    :return: 执行结果, 如果命令执行失败, 则返回错误信息
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return str(e)