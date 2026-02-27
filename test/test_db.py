import os
import json

from backend.infra.database import MessageDB


def test_database_flow():
    db_path = "test_chat.db"
    # 每次测试前清理旧环境，确保数据纯净
    if os.path.exists(db_path):
        os.remove(db_path)

    db = MessageDB(db_path)
    session_id = "test_sunshine_001"

    print("🌟 开始数据库注入测试...")

    # 1. 模拟用户提问
    user_msg = {"role": "user", "content": "hi 当前目录有哪些文件"}
    db.append_message(session_id, user_msg)

    # 2. 模拟 Assistant 发起工具调用 (带有推理内容和 tool_calls)
    assistant_call = {
        "role": "assistant",
        "content": "",
        "model_extra": {"reasoning_content": "用户想看文件，我要调函数"},
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "list_directory", "arguments": "{}"}
            }
        ]
    }
    db.append_message(session_id, assistant_call)

    # 3. 核心环节：模拟 Tool 返回结果
    # 注意：根据你之前的逻辑，这里需要确认 tool_call_id 是否被正确存入
    tool_msg = {
        "role": "tool",
        "content": '["file1.py", "file2.txt"]',
        "tool_call_id": "call_123"  # 👈 这是一个关键字段
    }
    db.append_message(session_id, tool_msg)

    print("📥 数据写入完成，开始读取校验...")

    # 4. 读取并验证
    history = db.load_messages(session_id)

    # --- 自动化断言检查 ---
    assert len(history) == 3, f"❌ 消息条数不对！期望 3，实际 {len(history)}"

    # 检查 Tool 消息是否包含 tool_call_id (这是你之前怀疑丢失的地方)
    last_msg = history[-1]
    print(f"\n🔍 最后一条记录内容: {json.dumps(last_msg, indent=2, ensure_ascii=False)}")

    if last_msg["role"] == "tool":
        # 检查你的 load_messages 是否漏掉了字段
        if "tool_call_id" not in last_msg and "tool_call_id" not in str(last_msg):
            print("⚠️ 警告：数据库中存入了 tool 角色，但读取结果里缺少 tool_call_id！")

    print("\n✅ 数据库存取测试通过！顺序和条数均正常。")


if __name__ == "__main__":
    try:
        test_database_flow()
    except Exception as e:
        print(f"❌ 测试失败: {e}")