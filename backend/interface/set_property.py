"""
    这个接口定义了用户如何去设置软件默认设置,Agent设置等“属性设置”
"""

def get_llm_settings():
    """
    这个是面向UI的,用于读取模型相关的默认设置,返回一个List[Dict],
    字典的key是模型名称,value是模型配置
    模型配置的结构为：
    [
        {config:"default",url: url, model: model, api_key: api_key},
        {config:"option_1",url: url, model: model, api_key: api_key},
        {config:"option_2",url: url, model: model, api_key: api_key},
        {config:"option_3",url: url, model: model, api_key: api_key},
        ...
    ]
    "default"是默认模型,url: url, model: model, api_key: api_key是模型配置
    url: 模型url
    model: 模型名称
    api_key: 模型api_key
    """
    pass

def set_llm_settings(settings: List[LLMSettingsProperty]):
    """
    这个是面向UI的,用于设置模型相关的默认设置,参数为List[LLMSettingsProperty],存储到配置文件中
    """
    pass