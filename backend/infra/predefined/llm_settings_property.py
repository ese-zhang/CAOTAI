from dataclasses import dataclass
from ..config import default_api_key,default_url,default_model

@dataclass
class LLMSettingsProperty:
    """
        一个llm_settings的属性
        它定义了llm_settings的属性
        :param model: 模型名称
        :param url: 模型url
        :param api_key: 模型api_key
    """
    model: str = default_model
    url: str = default_url
    api_key: str = default_api_key