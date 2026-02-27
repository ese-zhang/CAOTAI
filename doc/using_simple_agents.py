"""
在这个代码中我们完成understand_RDAS.py中的示例,使用简单Agent完成对话,不手动循环调用
"""
from backend.core.agent import basic_agent
from backend.infra.database import db
from backend.infra.predefined.llm_settings_property import LLMSettingsProperty

if __name__ == "__main__":
    llm_settings = LLMSettingsProperty()
    from backend.core.tools.register_tool import tools_list

    session_id = "sessions_01"
    db.clear_session(session_id)

    agent = basic_agent(
        name="Agent",
        description="你是一个有用的助手",
        skills=[],
        rules=[],
        soul="你是ENFJ小太阳，会热情回复",
        tools=tools_list,
        llm_settings=llm_settings
    )
    while True:
        request = input("请输入你的请求：")
        if request == "exit":
            break
        agent.run({"text": request, "session_id": session_id})
        print(db.load_messages(session_id)[-1])