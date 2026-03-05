import warnings
from typing import Callable, Dict, List

# 约定：注册的 callable 签名为 (ctx: ToolContext, **kwargs) -> Any，便于与外界解耦、可插拔测试
# 执行层负责构建 ToolContext 并传入，工具内部不依赖全局实例


class ToolManager:
    def __init__(self):
        self._registry: Dict[str, Callable] = {}
        self._schemas: Dict[str, dict] = {}

    def register(self, name: str, description: str, parameters: dict):
        """
        注册工具：func 签名为 (ctx: ToolContext, **kwargs)，由执行层注入 ctx。
        """

        def decorator(func: Callable):
            self._registry[name] = func
            self._schemas[name] = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            }
            return func

        return decorator

    def get_payload_components(self, tool_names: List[str],strict = False):
        """
        根据名称列表获取 tools 定义和 registry
        """
        tools_list = []
        registry_map = {}

        for name in tool_names:
            if name in self._schemas:
                tools_list.append(self._schemas[name])
                registry_map[name] = self._registry[name]
            else:
                msg = f"Tool '{name}' is not registered in ToolManager. It will be ignored."
                if strict:
                    raise ValueError(msg)
                else:
                    # 核心逻辑：如果找不到工具，触发警告
                    warnings.warn(
                        message=msg,
                        category=UserWarning,
                        stacklevel=2  # 让警告指向调用者
                    )

        return tools_list, registry_map