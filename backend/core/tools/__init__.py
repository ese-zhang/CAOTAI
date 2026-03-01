# 实例化全局管理器
from backend.infra.function_calling.toolmanager import ToolManager

tool_manager = ToolManager()

from . import register_tool as _
