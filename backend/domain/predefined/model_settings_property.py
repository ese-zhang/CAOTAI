from typing import Any, Callable, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, ConfigDict

"""
model_settings = {
            "model": string(model_name) | null,
                # 使用的模型名称
                # 选填；未提供时使用系统默认模型
            "url": string(url) | null,
                # LLM 服务的访问地址
                # 选填；未提供时使用默认 endpoint
            "api_key": string(api_key) | null,
                # 调用 LLM 所需的鉴权 key
                # 选填；未提供时使用默认凭据
            "tools": array<tool_definition>,
                # 可供 LLM 调用的工具（函数）定义列表
                # 每个 tool 描述一个可被模型触发的 function
            "tool_registry": map<string(tool_name), callable(tool_function)>
                # 工具注册表
                # key: tool_name(必须与 tools[].function.name 一致)
                # value: 实际可执行的函数对象
        }
        其中tool_definition的结构为:
        tool_definition = {
            "type": "function",
            "function": {
                "name": string(tool_name),
                    # 工具名称
                    # 用于模型生成 tool call 时的函数标识

                "description": string(tool_description),
                    # 工具功能描述
                    # 供模型理解“什么时候该调用该工具”

                "parameters": parameters_schema
                    # 工具参数定义(JSON Schema 子集)
                    # 用于模型生成 tool call 时的参数定义
            }
        }
        其中, parameters_schema的结构为:
        parameters_schema = {
            "type": "object",

            "properties": {
                property_name: {
                    "type": string | number | integer | boolean | array | object,
                        # 参数类型

                    "description": string(property_description),
                        # 参数含义说明，供模型理解与生成

                    "enum"?: array<literal>,
                        # 可选；限制参数取值范围（枚举）

                    "items"?: schema,
                        # 可选；当 type == array 时定义元素类型

                    "properties"?: schema,
                        # 可选；当 type == object 时定义字段结构

                    "required"?: array<string>
                        # 可选；当 type == object 时定义必填字段
                }
            },

            "required": array<string(property_name)>
                # 工具调用时必须提供的参数列表
        }
"""
# 1. 定义参数结构的递归模型 (JSON Schema 子集)
class PropertySchema(BaseModel):
    type: Literal["string", "number", "integer", "boolean", "array", "object"]
    description: str
    enum: Optional[List[Any]] = None
    items: Optional["PropertySchema"] = None  # 递归：用于 array
    properties: Optional[Dict[str, "PropertySchema"]] = None  # 递归：用于 object
    required: Optional[List[str]] = None


# 2. 定义函数详细信息
class FunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]  # 顶层通常是 {"type": "object", "properties": ..., "required": ...}


# 3. 定义工具包装器
class ToolDefinition(BaseModel):
    type: Literal["function"] = "function"
    function: FunctionDefinition


# 4. 完整的 ModelSettings 结构
class ModelSettings(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # 允许存储 callable

    model: Optional[str] = None
    url: Optional[str] = None
    api_key: Optional[str] = None
    tools: List[ToolDefinition] = Field(default_factory=list)
    tool_registry: Dict[str, Callable] = Field(default_factory=dict)

    def to_payload(self) -> dict:
        """导出为符合 API 规范的字典"""
        return self.model_dump()