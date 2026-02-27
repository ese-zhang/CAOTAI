from . import tool_manager
import subprocess

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
def list_directory(path: str,depth: int) -> list: 
    """
        列出指定路径下的所有文件和文件夹
        :param path: 要列出的路径
        :param depth: 深度,-1为所有
        :return: 文件和文件夹的列表
    """
    pass


@tool_manager.register(
    name="list_modules",
    description="列出指定文件内的所有类或函数",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "要列出的文件路径"},
            "module_depth": {"type": "integer", "description": "模块的深度,正整数,0为当前文件,1为当前文件的子模块,2为当前文件的子模块的子模块,以此类推"}
        },
        "required": ["file_path", "module_depth"]
    }
)
def list_modules(file_path: str,module_depth: int) -> list:
    """
        列出指定文件内的所有模块
        :param file_path: 要列出的python文件路径
        :param module_depth: 模块的深度,正整数
        :return: 模块的列表
    """
    pass

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
def read_file(path: str,start_lines:int,end_lines:int) -> str:
    """
        读取指定路径下的文件,并返回指定行数的内容,
        如果差距超过阈值, 则返回start_lines到阈值行数的内容, 并提示用户需要读取更多行数
        :param path: 要读取的文件路径
        :param start_lines: 开始行数
        :param end_lines: 结束行数
        :return: 指定行数的内容, 如果差距超过阈值, 则返回start_lines到阈值行数的内容, 并提示用户需要读取更多行数
    """
    pass

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
    pass


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
    pass


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
def apply_diff(file_path: str, search_block: str, replace_block: str, occurence: list[int] = [1], allow_fuzzy: bool = False) -> str:
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
    pass

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
        with open(file_path, "w") as f:
            f.write(content)
        return True
    except Exception as e:
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