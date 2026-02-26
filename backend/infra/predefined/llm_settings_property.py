from dataclasses import dataclass
from ..config import DEFAULT_API_KEY,DEFAULT_URL,DEFAULT_MODEL

@dataclass
class LLMSettingsProperty:
    """
        一个llm_settings的属性
        它定义了llm_settings的属性
        :param model: 模型名称
        :param url: 模型url
        :param api_key: 模型api_key
    """
    model: str = DEFAULT_MODEL
    url: str = DEFAULT_URL
    api_key: str = DEFAULT_API_KEY