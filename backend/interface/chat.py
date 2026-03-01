"""
    这个接口定义了在UI中如何去与Agent进行对话, 如开始对话、继续对话、删除结束对话
"""
from backend.infra.database import db
from typing import Tuple

def start_chat(agent_name: str)->Tuple[str, str]:
    """
        这个接口用于从0开始一次对话
        用户需要指定一个Agent, 并输入请求，
        程序向db发送一个创建会话的请求,并返回会话id
    """
    session_id = db.get_new_session_id() # 获取一个之前没有使用过的会话id
    db.create_session_for_agent(session_id, agent_name) # 创建一个会话，并绑定到指定的Agent
    # 从Agent配置构建Agent
    
    return session_id, f"Session {session_id}"

def continue_chat(session_id: str):
    """
        这个接口用于继续一次对话
    """
    pass

def delete_chat(session_id: str):
    """
        这个接口用于删除一次对话
    """
    pass