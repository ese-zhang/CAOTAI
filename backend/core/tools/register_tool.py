from . import tool_manager

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