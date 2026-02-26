from openai import OpenAI
from backend.infra.config import DEFAULT_API_KEY, DEFAULT_URL, DEFAULT_MODEL  # 导入默认配置
from backend.core.request_display_action_and_save import request_display_action_and_save
from backend.infra.database import db
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
    session_id = "sessions_01"  # 建议用唯一的 ID
    user_message = {"role": "user", "content": "帮我查一下北京的天气。"}

    # 2. 【核心】通过 memory_manager 初始化 session 并存入第一条消息
    # 这步会调用 db.append_message，确保数据库里有了 user 消息
    db.clear_session(session_id)
    db.append_message(session_id, user_message)
    client = OpenAI(api_key=DEFAULT_API_KEY,
                    base_url=DEFAULT_URL)
    model_settings = {
        "model": DEFAULT_MODEL,
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
    request_display_action_and_save(client=client, session_path=session_id, model_settings=model_settings)
    print(db.load_messages(session_id=session_id))
    #request_display_action_and_save(client=client, session_path="sessions.json", model_settings=model_settings)