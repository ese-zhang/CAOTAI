"""
    在这个代码中我们定义了一个Agent基类, 这个基础类定义了Agent的属性,与运行方法
"""
from openai import OpenAI
from .request_display_action_and_save import request_display_action_and_save
from ..infra.predefined.llm_settings_property import LLMSettingsProperty
from .tools import tool_manager
from ..infra.predefined.model_settings_property import ModelSettings
from ..infra.database import db
class basic_agent:
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
        llm_settings: LLMSettingsProperty = LLMSettingsProperty(), # llm的配置，默认选择系统默认配置
        **kwargs, # 其他参数
        ): # 初始化Agent的属性, 包括名称、描述、技能、规则、系统提示、工具、模型设置
        self.name = name
        self.description = description
        self.skills = skills
        self.rules = "\n".join(rules)
        self.soul = soul
        self.tools = tools
        self.llm_settings = llm_settings

        # 1. 从管理器获取允许使用的工具定义和可执行函数列表
        tools_defs, registry = tool_manager.get_payload_components(tools)
        
        # 2. 构建类型安全的 ModelSettings 对象
        self.model_settings = ModelSettings(
            model=llm_settings.model,
            url=llm_settings.url,
            api_key=llm_settings.api_key,
            tools=tools_defs, # 自动解析为 ToolDefinition 列表
            tool_registry=registry
        )

        #**kwargs, 如果出现basic_agent(params=params)，存储为self.params=params
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.client = OpenAI(api_key=self.llm_settings.api_key,
                    base_url=self.llm_settings.url)
    
    def get_payload(self):
        """生成最终发送给 LLM 的配置字典"""
        return self.model_settings.to_payload()
    
    def run(self,request: dict):
        """
            运行Agent, 指定RDAS过程, 直到没有进一步动作, 给出最终答案
            request: 用户请求,包括用户输入的文本，以及上下文存储的文件路径
            格式为: {"text": "用户输入的文本", "session_id": "上下文存储的文件路径"}
            运行这个指令，等效于用户输入了命令，并且按下了回车键
        """
        system = self.prompt_builder()
        db.append_message(request["session_id"], system)
        messages={"role": "user", "content": request["text"]}
        db.append_message(request["session_id"], messages)
        # while循环，直到返回值是False
        while True:
            is_final_answer = request_display_action_and_save(
                client=self.client,
                session_id=request["session_id"],
                model_settings=self.get_payload()
            )
            if is_final_answer:
                break
        return is_final_answer

    def prompt_builder(self):
            """
            构建提示词
            提示词的格式是：系统提示词+用户提问
            系统提示词=模型灵魂(soul.md)+模型原则(rules.md)+技能(skills.md的摘要聚合)+工具(tools的摘要聚合),记录在role:system字段中
            """
            system_prompt = ""
            # system_prompt += self.soul + "\n" + self.rules + "\n" + "\n" + tool_manager.get_tool_prompt(self.tools)
            skills = "当你要开始一个工作时，需要使用search_skills获取可能的SOP"
            components = [self.soul, self.rules, skills]
            system_prompt = "\n".join(filter(None, components))
            return {"role": "system", "content": system_prompt}
