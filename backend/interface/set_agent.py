"""
    这个接口定义了UI如何去设置Agent的属性, 如创建、编辑、删除、获取属性、获取列表等
"""

def create_agent():
    """
        这个接口用于创建并保存一个Agent, 并持久化到硬盘中
    """
    pass

def edit_agent():
    """
        这个接口用于编辑一个Agent, 并持久化到硬盘中
    """
    pass

def delete_agent():
    """
        这个接口用于删除一个Agent
    """
    pass

def get_agent_property(agent_name: str)->dict:
    """
        这个接口用于从硬盘中获取一个Agent的属性
        参数为Agent名称, 返回一个字典, 字典的key为Agent的属性, value为Agent的属性值, 如果Agent不存在, 返回None
        字典的key为:
        - name: Agent名称
        - description: Agent描述
        - skills: Agent技能列表
        - rules: Agent规则列表
        - soul: Agent灵魂
        - tools: Agent工具列表
        - llm_settings: Agent模型设置
    """
    pass

def get_agent_list():
    """
        这个接口用于获取所有Agent的列表
    """