import pytest
from typing import Callable
from pydantic import ValidationError

from backend.core.agent import basic_agent
from backend.core.tools import ToolManager, tool_manager
from backend.infra.predefined.llm_settings_property import LLMSettingsProperty
from backend.infra.predefined.model_settings_property import ModelSettings, PropertySchema


# --- 1. ModelSettings 结构测试 (Schema Validation) ---

def test_model_settings_validation():
    """测试 ModelSettings 是否能正确拦截错误的格式"""
    # 正常情况
    settings = ModelSettings(
        model="gpt-4",
        tool_registry={"test_func": lambda x: x}
    )
    assert settings.model == "gpt-4"
    assert callable(settings.tool_registry["test_func"])

    # 异常情况：tools 必须是列表
    with pytest.raises(ValidationError):
        ModelSettings(tools="not a list")


def test_property_schema_recursive():
    """测试递归 Schema 是否支持嵌套对象"""

    # 模拟一个嵌套的 Object 参数
    schema = PropertySchema(
        type="object",
        description="用户信息",
        properties={
            "address": PropertySchema(
                type="object",
                description="地址",
                properties={
                    "city": PropertySchema(type="string", description="城市")
                }
            )
        }
    )
    assert schema.properties["address"].properties["city"].type == "string"


# --- 2. ToolManager 注册逻辑测试 ---

def test_tool_registration():
    """测试工具是否能正确注册并生成 Payload 组件"""
    tm = ToolManager()

    @tm.register(
        name="add",
        description="加法运算",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"]
        }
    )
    def add_func(a, b):
        return a + b

    defs, registry = tm.get_payload_components(["add"])

    assert len(defs) == 1
    assert defs[0]["function"]["name"] == "add"
    assert registry["add"](1, 2) == 3


# --- 3. Agent 集成与 Payload 生成测试 ---

def test_agent_payload_generation():
    """测试从 Agent 初始化到最终 Payload 字典的转换"""
    tm = tool_manager

    # 注册一个模拟工具
    @tm.register("get_stock", "获取股价", {"type": "object", "properties": {}})
    def get_stock(): pass

    # 模拟外部传入的配置
    base_config = LLMSettingsProperty(model="deepseek-V3",api_key="sk-123")

    agent = basic_agent(
        name="金融助手",
        description="分析股票",
        skills=[],
        rules=[],
        soul="你是个分析师",
        tools=["get_stock"],  # 只传名称
        llm_settings=base_config,
        custom_param="special_value"  # 测试 kwargs
    )

    # 生成最终 payload
    payload = agent.get_payload()

    # 断言结构符合你的规范
    assert payload["model"] == "deepseek-V3"
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["function"]["name"] == "get_stock"
    assert "get_stock" in payload["tool_registry"]
    assert agent.custom_param == "special_value"

def test_agent_payload_generation_with_error_tools():
    """测试tool列表找不到工具的报错"""
    tm = tool_manager

    # 注册一个错误的模拟工具
    @tm.register("get_stocsk", "获取股价", {"type": "object", "properties": {}})
    def get_stock(): pass

    # 模拟外部传入的配置
    base_config = LLMSettingsProperty(model="deepseek-V3",api_key="sk-123")

    with pytest.warns(UserWarning):
        agent = basic_agent(
            name="金融助手",
            description="分析股票",
            skills=[],
            rules=[],
            soul="你是个分析师",
            tools=["get_stocks"],  # 只传名称
            llm_settings=base_config,
            custom_param="special_value"  # 测试 kwargs
        )

    # 生成最终 payload
    payload = agent.get_payload()

    # 断言结构符合你的规范
    assert payload["model"] == "deepseek-V3"
    assert len(payload["tools"]) == 0
    assert "get_stocks" not in payload["tool_registry"]
    assert agent.custom_param == "special_value"

def test_missing_tool_handling():
    """测试请求了未注册的工具时，是否能平稳处理（不报错但 registry 为空）"""
    tm = ToolManager()
    defs, registry = tm.get_payload_components(["non_existent_tool"])
    assert len(defs) == 0
    assert len(registry) == 0