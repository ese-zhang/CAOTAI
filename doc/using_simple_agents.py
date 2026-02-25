"""
在这个代码中我们完成understand_RDAS.py中的示例,使用简单Agent完成对话,不手动循环调用
"""
from backend.core.agent import basic_agent
from backend.infra.predefined.llm_settings_property import LLMSettingsProperty
from backend.infra.fileio import load_messages

if __name__ == "__main__":
    llm_settings = LLMSettingsProperty()
    agent = basic_agent(
        name="Agent",
        description="一个简单的Agent，可以获取指定城市的天气",
        skills=[],
        rules=[],
        soul="你是ENFJ小太阳，会热情回复",
        tools=["get_weather"],
        llm_settings=llm_settings
    )
    request = input("请问你有什么需求呢：")
    session_path = f"sessions_report.json"
    agent.run({"text": request, "session_path": session_path})
    print(load_messages(session_path))