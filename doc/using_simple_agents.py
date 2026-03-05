"""
在这个代码中我们完成 understand_RDAS.py 中的示例，使用简单 Agent 完成对话，不手动循环调用。
工作区固定为当前脚本所在目录（doc/），Agent 的文件类工具仅在此目录下生效。
"""
from pathlib import Path

from backend.app.agent import basic_agent
from backend.infra.database import db

if __name__ == "__main__":
    from backend.infra.function_calling.register_tool import tools_list

    # 工作区：Agent 只能在此目录下执行 list_directory / read_file 等文件操作
    workspace_root = Path(__file__).resolve().parent

    session_id = "sessions_01"
    db.clear_session(session_id)

    agent = basic_agent(
        name="Agent",
        description="你是一个有用的助手",
        skills=[],
        rules=[],
        soul="你是ENFJ小太阳，会热情回复",
        tools=tools_list,
        workspace_root=str(workspace_root),
    )
    while True:
        request = input("请输入你的请求：")
        if request == "exit":
            break
        agent.run({"text": request, "session_id": session_id})
        #print(db.load_messages(session_id)[-1])