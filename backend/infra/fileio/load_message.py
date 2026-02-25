import json
def load_messages(session_path: str) -> list[dict]:
    """
    从指定路径读取json文件, 获取messages
    :param session_path: 对话历史文件路径
    :return: 对话历史
    """
    # 从指定路径读取json文件，获取messages
    with open(session_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        messages = data["messages"]
    return messages if messages else []


def save_messages(messages: list[dict], session_path: str):
    """
    将对话历史保存到指定路径的json文件中
    :param messages: 对话历史
    :param session_path: 对话历史文件路径
    """
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump({"messages": messages}, f, ensure_ascii=False)
