from openai import OpenAI
from backend.infra.config import default_api_key, default_url, default_model  # 导入默认配置
from backend.core.request_display_action_and_save import request_display_action_and_save
from backend.infra.fileio import save_messages

"""
    这是一个示例, 展示如何使用RDAS模型
    定义：
    RDAS = Reasoning, Display, Action, Save
    Reasoning: 远程模型进行思考
    Display: UI进行展示
    Action: 本地进行动作
    Save: 对话历史进行保存
    通过RDAS模型, 结合循环与对话历史持久化,可以实现一个完整的Agent
"""
def get_weather(city: str):
    return f"城市{city}的天气是晴天"

if __name__ == "__main__":
    messages = [{"role": "user", "content": "帮我查一下北京的天气。"}]
    
    save_messages(messages, "sessions.json")
    client = OpenAI(api_key=default_api_key,
                    base_url=default_url)
    model_settings = {
        "model": default_model,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "获取指定城市的天气",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "城市名称，如北京、上海"}
                        },
                        "required": ["city"]
                    }
                }
            }
        ],
        "tool_registry": {
            "get_weather": get_weather
        }
    }
    request_display_action_and_save(client=client, session_path="sessions.json", model_settings=model_settings)
    request_display_action_and_save(client=client, session_path="sessions.json", model_settings=model_settings)