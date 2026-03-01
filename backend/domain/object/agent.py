"""
    在这个代码中我们定义了一个Agent基类, 这个基础类定义了Agent的属性,与运行方法
"""
from abc import ABC
from backend.config import DEFAULT_MODEL, DEFAULT_API_KEY, DEFAULT_URL
from ..predefined.property import LLMSettingsProperty


class basic_agent(ABC):
    """
        一个Agent基础类
        它定义了Agent的属性
        :param name: Agent的名称
        :param description: Agent的描述
        :param skills: Agent的技能列表
        :param rules: Agent的规则
        :param soul: Agent的灵魂
        :param tools: Agent的工具列表
        :param llm_settings: LLM 运行配置
        :param kwargs: 其他参数
        :return: 初始化Agent的属性, 包括名称、描述、技能、规则、系统提示、工具
    """
    def __init__(self, 
        name: str, # Agent的名称
        description: str, # Agent的描述，用于描述Agent的职责与能力
        skills: list[str], # Agent的技能列表
        rules: list[str], # Agent的规则，用于描述Agent的行为与策略
        soul: str, # Agent的灵魂，用于配置Agent的行为与策略
        tools: list[str], # Agent的工具列表
        llm_settings: LLMSettingsProperty=None, # llm的配置，默认选择系统默认配置
        **kwargs, # 其他参数
        ): # 初始化Agent的属性, 包括名称、描述、技能、规则、系统提示、工具、模型设置
        self.model_settings = None # 通过其它参数构建
        self.name = name
        self.description = description
        self.skills = skills
        self.rules = rules
        self.soul = soul
        self.tools = tools
        if llm_settings is None:
            self.llm_settings = LLMSettingsProperty(model=DEFAULT_MODEL,url=DEFAULT_URL,api_key=DEFAULT_API_KEY)
        else:
            self.llm_settings = llm_settings
        
        # 2. 构建类型安全的 ModelSettings 对象
        self._build_model_settings()

        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def _get_payload(self):
        """生成最终发送给 LLM 的配置字典"""
        return self.model_settings.to_payload()
    
    def think(self,request: dict):
        pass

    def _build_prompt(self):
        pass

    def _build_model_settings(self):
        # self.model_settings = ModelSettings(
        #     model=self.llm_settings.model,
        #     url=self.llm_settings.url,
        #     api_key=self.llm_settings.api_key,
        #     tools=tools_defs, # 自动解析为 ToolDefinition 列表
        #     tool_registry=registry
        # )
        pass